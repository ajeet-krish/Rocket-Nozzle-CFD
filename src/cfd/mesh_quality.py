"""Mesh quality metrics and validation."""
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import numpy as np


class _ParsedMesh(NamedTuple):
    """Parsed SU2 mesh data."""

    nodes: np.ndarray  # (N, 3) node coordinates
    elements: np.ndarray  # (M, 5) element connectivity: type, n1, n2, n3, n4
    markers: dict[str, list[tuple[int, ...]]]  # {tag: [(type, n1, n2, ...), ...]}


@dataclass
class MeshQualityResult:
    """Mesh quality assessment results.

    Attributes:
        n_nodes: Number of mesh nodes
        n_elements: Number of mesh elements
        min_orthogonality: Minimum orthogonality angle (degrees)
        max_aspect_ratio: Maximum aspect ratio
        max_expansion_ratio: Maximum cell expansion ratio
        has_negative_jacobians: Whether mesh has negative Jacobians
        passed: Whether mesh passes all quality checks
        notes: Additional notes about mesh quality
    """

    n_nodes: int
    n_elements: int
    min_orthogonality: float
    max_aspect_ratio: float
    max_expansion_ratio: float
    has_negative_jacobians: bool
    passed: bool
    notes: str


def _parse_su2_mesh(mesh_file: Path) -> _ParsedMesh:
    """Parse SU2 mesh file.

    The SU2 format uses plain text with sections for elements, nodes, and
    boundary markers. Element connectivity is stored as integer indices.

    Args:
        mesh_file: Path to .su2 mesh file

    Returns:
        _ParsedMesh containing nodes, elements, and markers

    Raises:
        ValueError: If the mesh file is malformed or empty
    """
    with open(mesh_file, "r") as f:
        lines = f.readlines()

    nodes: list[list[float]] = []
    elements: list[list[int]] = []
    markers: dict[str, list[tuple[int, ...]]] = {}

    section = None
    marker_tag = None
    marker_elems_remaining = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Check for section headers
        if line.startswith("NDIME="):
            section = "ndime"
            continue
        elif line.startswith("NELEM="):
            section = "elements"
            continue
        elif line.startswith("NPOIN="):
            section = "nodes"
            continue
        elif line.startswith("NMARK="):
            section = "markers"
            continue
        elif line.startswith("MARKER_TAG="):
            marker_tag = line.split("=", 1)[1].strip()
            markers[marker_tag] = []
            section = "marker_tag"
            continue
        elif line.startswith("MARKER_ELEMS="):
            marker_elems_remaining = int(line.split("=", 1)[1].strip())
            section = "marker_elems"
            continue

        # Parse data based on current section
        if section == "elements":
            parts = line.split()
            elem_type = int(parts[0])
            # SU2 element type 9 = quad (4 nodes), type 3 = line (2 nodes)
            # For 2D quads: type n1 n2 n3 n4
            connectivity = [int(p) for p in parts[1:]]
            elements.append([elem_type] + connectivity)
        elif section == "nodes":
            parts = line.split()
            # Format: x y z (or x y for 2D, but we add z=0)
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2]) if len(parts) > 2 else 0.0
            nodes.append([x, y, z])
        elif section == "marker_elems" and marker_tag is not None:
            if marker_elems_remaining > 0:
                parts = line.split()
                elem_type = int(parts[0])
                connectivity = [int(p) for p in parts[1:]]
                markers[marker_tag].append((elem_type, *connectivity))
                marker_elems_remaining -= 1
                if marker_elems_remaining == 0:
                    section = "markers"

    if not nodes:
        raise ValueError(f"No nodes found in mesh file: {mesh_file}")
    if not elements:
        raise ValueError(f"No elements found in mesh file: {mesh_file}")

    return _ParsedMesh(
        nodes=np.array(nodes, dtype=np.float64),
        elements=np.array(elements, dtype=np.int64),
        markers=markers,
    )


def _element_center(
    nodes: np.ndarray,
    elem_conn: np.ndarray,
) -> np.ndarray:
    """Compute the centroid of an element.

    Args:
        nodes: Full node coordinate array
        elem_conn: Element connectivity (type, n1, n2, ...) - only node indices used

    Returns:
        (3,) centroid coordinates
    """
    # Node indices are everything after the element type
    node_indices = elem_conn[1:]
    return nodes[node_indices].mean(axis=0)


def _element_area_quad(nodes: np.ndarray, elem_conn: np.ndarray) -> float:
    """Compute area of a quad element using the shoelace formula.

    For a quad with nodes n1, n2, n3, n4 (in order), the area is computed
    as the sum of two triangle areas.

    Args:
        nodes: Full node coordinate array
        elem_conn: Element connectivity (type, n1, n2, n3, n4)

    Returns:
        Area of the element
    """
    node_indices = elem_conn[1:]  # Skip element type
    coords = nodes[node_indices]  # (4, 3) or (4, 2)

    # Use the cross product of diagonals for quad area
    # For quad n1-n2-n3-n4: area = 0.5 * |(n3-n1) x (n2-n4)|
    v1 = coords[2] - coords[0]  # diagonal n1->n3
    v2 = coords[1] - coords[3]  # diagonal n4->n2

    # Cross product (works for 3D, z-component for 2D)
    cross = np.cross(v1, v2)
    if cross.ndim == 0:
        return 0.5 * abs(float(cross))
    return 0.5 * abs(float(cross[2]))


def _edge_length(nodes: np.ndarray, n1: int, n2: int) -> float:
    """Compute Euclidean distance between two nodes."""
    diff = nodes[n2] - nodes[n1]
    return float(np.linalg.norm(diff))


def _face_nodes_from_elements(
    nodes: np.ndarray,
    elem1_conn: np.ndarray,
    elem2_conn: np.ndarray,
) -> tuple[int, int] | None:
    """Find the two shared nodes between two adjacent elements.

    For quad elements sharing an edge, exactly 2 nodes are shared.

    Args:
        nodes: Node coordinate array
        elem1_conn: First element connectivity
        elem2_conn: Second element connectivity

    Returns:
        Tuple of (node_a, node_b) if they share an edge, else None
    """
    idx1 = set(elem1_conn[1:])
    idx2 = set(elem2_conn[1:])
    shared = idx1 & idx2
    if len(shared) == 2:
        return tuple(sorted(shared))  # type: ignore[return-value]
    return None


def _compute_orthogonality(
    nodes: np.ndarray,
    elements: np.ndarray,
) -> np.ndarray:
    """Compute orthogonality angle for each interior face.

    Orthogonality is the angle between the face normal and the vector
    connecting the two adjacent element centers. For a perfectly
    orthogonal mesh, this angle is 90 degrees.

    Args:
        nodes: (N, 3) node coordinates
        elements: (M, 5) element connectivity

    Returns:
        Array of orthogonality angles (degrees) for each interior face
    """
    n_elements = len(elements)
    if n_elements < 2:
        return np.array([])

    # Build a face-to-elements mapping: face (min_node, max_node) -> list of element indices
    face_to_elems: dict[tuple[int, int], list[int]] = {}
    for i, elem in enumerate(elements):
        node_indices = elem[1:]  # Skip element type
        n_nodes_elem = len(node_indices)
        for j in range(n_nodes_elem):
            n1 = int(node_indices[j])
            n2 = int(node_indices[(j + 1) % n_nodes_elem])
            face_key = (min(n1, n2), max(n1, n2))
            if face_key not in face_to_elems:
                face_to_elems[face_key] = []
            face_to_elems[face_key].append(i)

    # Compute element centers
    centers = np.array([
        _element_center(nodes, elem) for elem in elements
    ])

    orthogonality_angles: list[float] = []

    for face_key, elem_indices in face_to_elems.items():
        if len(elem_indices) != 2:
            continue  # Boundary face or non-manifold

        i, j = elem_indices
        n1_idx, n2_idx = face_key

        # Face normal vector (in 2D, perpendicular to the face)
        face_vec = nodes[n2_idx] - nodes[n1_idx]
        # Normal is perpendicular to face vector (rotate 90 degrees in 2D)
        face_normal = np.array([-face_vec[1], face_vec[0], 0.0])
        norm_len = np.linalg.norm(face_normal)
        if norm_len < 1e-15:
            continue
        face_normal /= norm_len

        # Vector connecting element centers
        center_vec = centers[j] - centers[i]
        center_norm = np.linalg.norm(center_vec)
        if center_norm < 1e-15:
            continue
        center_vec /= center_norm

        # Orthogonality metric: for a perfectly orthogonal mesh, the face normal
        # is parallel to the center-to-center vector (angle = 0 degrees).
        # We report orthogonality as 90 - angle, so a perfectly orthogonal mesh
        # scores 90 degrees and a maximally skewed mesh scores 0 degrees.
        # Use absolute dot product to handle sign ambiguity (normal can point
        # either way along the same line).
        cos_angle = np.abs(np.dot(face_normal, center_vec))
        cos_angle = np.clip(cos_angle, 0.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)

        # Orthogonality = 90 - deviation from parallel
        orthogonality_angles.append(90.0 - angle_deg)

    return np.array(orthogonality_angles) if orthogonality_angles else np.array([])


def _compute_aspect_ratio(nodes: np.ndarray, elements: np.ndarray) -> np.ndarray:
    """Compute aspect ratio for each element.

    Aspect ratio = max_edge_length / min_edge_length.
    Ideal: 1.0 (square). Typical limit: < 100.

    Args:
        nodes: (N, 3) node coordinates
        elements: (M, 5) element connectivity

    Returns:
        Array of aspect ratios, one per element
    """
    aspect_ratios: list[float] = []

    for elem in elements:
        node_indices = elem[1:]  # Skip element type
        n_nodes_elem = len(node_indices)

        if n_nodes_elem < 2:
            continue

        # Compute all edge lengths
        edge_lengths = []
        for j in range(n_nodes_elem):
            n1 = int(node_indices[j])
            n2 = int(node_indices[(j + 1) % n_nodes_elem])
            edge_lengths.append(_edge_length(nodes, n1, n2))

        if not edge_lengths:
            continue

        min_edge = min(edge_lengths)
        max_edge = max(edge_lengths)

        if min_edge < 1e-15:
            aspect_ratios.append(float("inf"))
        else:
            aspect_ratios.append(max_edge / min_edge)

    return np.array(aspect_ratios) if aspect_ratios else np.array([])


def _compute_expansion_ratio(
    nodes: np.ndarray,
    elements: np.ndarray,
) -> np.ndarray:
    """Compute expansion ratio between adjacent elements.

    Expansion ratio = max(area_i, area_j) / min(area_i, area_j).
    Ideal: 1.0. Typical limit: < 2.0.

    Args:
        nodes: (N, 3) node coordinates
        elements: (M, 5) element connectivity

    Returns:
        Array of expansion ratios for each interior face
    """
    n_elements = len(elements)
    if n_elements < 2:
        return np.array([])

    # Compute element areas
    areas = np.array([
        _element_area_quad(nodes, elem) for elem in elements
    ])

    # Build face-to-elements mapping
    face_to_elems: dict[tuple[int, int], list[int]] = {}
    for i, elem in enumerate(elements):
        node_indices = elem[1:]
        n_nodes_elem = len(node_indices)
        for j in range(n_nodes_elem):
            n1 = int(node_indices[j])
            n2 = int(node_indices[(j + 1) % n_nodes_elem])
            face_key = (min(n1, n2), max(n1, n2))
            if face_key not in face_to_elems:
                face_to_elems[face_key] = []
            face_to_elems[face_key].append(i)

    expansion_ratios: list[float] = []

    for elem_indices in face_to_elems.values():
        if len(elem_indices) != 2:
            continue  # Boundary face

        i, j = elem_indices
        area_i = areas[i]
        area_j = areas[j]

        if min(area_i, area_j) < 1e-15:
            expansion_ratios.append(float("inf"))
        else:
            expansion_ratios.append(max(area_i, area_j) / min(area_i, area_j))

    return np.array(expansion_ratios) if expansion_ratios else np.array([])


def _detect_negative_jacobians(
    nodes: np.ndarray,
    elements: np.ndarray,
) -> bool:
    """Detect if any elements have negative Jacobians.

    For a quad element with nodes in order, the Jacobian is positive if
    the nodes are ordered counter-clockwise. A negative Jacobian indicates
    an inverted or degenerate element.

    Args:
        nodes: (N, 3) node coordinates
        elements: (M, 5) element connectivity

    Returns:
        True if any element has a negative Jacobian
    """
    for elem in elements:
        node_indices = elem[1:]
        if len(node_indices) < 3:
            continue

        coords = nodes[node_indices]
        # Compute signed area using shoelace formula (z-component of cross product)
        # For 2D, this is the determinant-based area
        x = coords[:, 0]
        y = coords[:, 1]
        signed_area = 0.0
        n = len(x)
        for k in range(n):
            k_next = (k + 1) % n
            signed_area += x[k] * y[k_next] - x[k_next] * y[k]

        if signed_area < -1e-10:
            return True

    return False


def check_mesh_quality(mesh_file: Path, **kwargs: float) -> MeshQualityResult:
    """Check mesh quality metrics.

    Parses the SU2 mesh file and computes orthogonality, aspect ratio,
    and expansion ratio metrics.

    Args:
        mesh_file: Path to .su2 mesh file
        **kwargs: Optional threshold overrides:
            - min_orthogonality: Minimum acceptable orthogonality (default 20.0)
            - max_aspect_ratio: Maximum acceptable aspect ratio (default 100.0)
            - max_expansion_ratio: Maximum acceptable expansion ratio (default 2.0)

    Returns:
        MeshQualityResult with quality assessment
    """
    min_ortho = kwargs.get("min_orthogonality", 20.0)
    max_ar = kwargs.get("max_aspect_ratio", 100.0)
    max_er = kwargs.get("max_expansion_ratio", 2.0)

    if not mesh_file.exists():
        return MeshQualityResult(
            n_nodes=0,
            n_elements=0,
            min_orthogonality=0.0,
            max_aspect_ratio=float("inf"),
            max_expansion_ratio=float("inf"),
            has_negative_jacobians=False,
            passed=False,
            notes="Mesh file does not exist",
        )

    try:
        parsed = _parse_su2_mesh(mesh_file)
    except (ValueError, OSError) as exc:
        return MeshQualityResult(
            n_nodes=0,
            n_elements=0,
            min_orthogonality=0.0,
            max_aspect_ratio=float("inf"),
            max_expansion_ratio=float("inf"),
            has_negative_jacobians=False,
            passed=False,
            notes=f"Failed to parse mesh: {exc}",
        )

    n_nodes = len(parsed.nodes)
    n_elements = len(parsed.elements)

    # Compute quality metrics
    orthogonality = _compute_orthogonality(parsed.nodes, parsed.elements)
    aspect_ratio = _compute_aspect_ratio(parsed.nodes, parsed.elements)
    expansion_ratio = _compute_expansion_ratio(parsed.nodes, parsed.elements)
    has_neg_jac = _detect_negative_jacobians(parsed.nodes, parsed.elements)

    # Extract scalar metrics
    min_orthogonality = float(np.min(orthogonality)) if len(orthogonality) > 0 else 0.0
    max_aspect = float(np.max(aspect_ratio)) if len(aspect_ratio) > 0 else float("inf")
    max_expansion = float(np.max(expansion_ratio)) if len(expansion_ratio) > 0 else float("inf")

    # Determine pass/fail
    passed = (
        not has_neg_jac
        and min_orthogonality >= min_ortho
        and max_aspect <= max_ar
        and max_expansion <= max_er
    )

    # Build notes
    notes_parts = [f"Nodes: {n_nodes}, Elements: {n_elements}"]
    if len(orthogonality) > 0:
        mean_ortho = float(np.mean(orthogonality))
        notes_parts.append(f"Ortho: min={min_orthogonality:.1f} mean={mean_ortho:.1f} deg")
    if len(aspect_ratio) > 0:
        mean_ar = float(np.mean(aspect_ratio))
        notes_parts.append(f"AR: max={max_aspect:.1f} mean={mean_ar:.1f}")
    if len(expansion_ratio) > 0:
        mean_er = float(np.mean(expansion_ratio))
        notes_parts.append(f"ER: max={max_expansion:.2f} mean={mean_er:.2f}")
    if has_neg_jac:
        notes_parts.append("WARNING: Negative Jacobians detected")

    return MeshQualityResult(
        n_nodes=n_nodes,
        n_elements=n_elements,
        min_orthogonality=min_orthogonality,
        max_aspect_ratio=max_aspect,
        max_expansion_ratio=max_expansion,
        has_negative_jacobians=has_neg_jac,
        passed=passed,
        notes="; ".join(notes_parts),
    )


def validate_su2_mesh(mesh_file: Path) -> bool:
    """Validate that mesh file is readable by SU2.

    Checks that the mesh file contains all required boundary markers.

    Args:
        mesh_file: Path to .su2 mesh file

    Returns:
        True if mesh file has all required markers
    """
    try:
        with open(mesh_file, "r") as f:
            content = f.read()
        for marker in ["inlet", "outlet", "wall", "symmetry"]:
            if f"MARKER_TAG= {marker}" not in content:
                return False
        return True
    except Exception:
        return False
