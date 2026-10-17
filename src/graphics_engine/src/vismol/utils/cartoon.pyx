#!python
#cython: language_level=3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright 2022 Carlos Eduardo Sequeiros Borja <carseq@amu.edu.pl>
#  

cimport numpy
import cython
import numpy as np


cpdef float[:] cubic_hermite_interpolate(p_k1, tan_k1, p_k2, tan_k2, float t):
    result = np.copy(p_k1)
    cdef float tt, tmt_t, h00, h01, h10, h11
    tt = t * t
    tmt_t = 3.0 - 2.0 * t
    h01 = tt * tmt_t
    h00 = 1.0 - h01
    h10 = tt * (t - 2.0) + t
    h11 = tt * (t - 1.0)
    result *= h00
    result += tan_k1 * h10
    result += p_k2 * h01
    result += tan_k2 * h11
    return result

cpdef catmull_rom_spline(float[:,:] points, int num_points, int subdivs,
                         float strength=0.6, bint circular=False):
    # When I programmed this function, only God and me knew about its internal
    # structure. Now only God knows about it (-_-')
    cdef Py_ssize_t out_len
    if circular:
        out_len = num_points * subdivs
    else:
        out_len = (num_points - 1) * subdivs + 1
    out_coords = np.empty([out_len, 3], dtype=np.float32)
    cdef Py_ssize_t index = 0
    cdef float dt = 1.0 / subdivs
    tan_k1 = np.zeros(3, dtype=np.float32)
    tan_k2 = np.zeros(3, dtype=np.float32)
    p_k1 = np.zeros(3, dtype=np.float32)
    p_k2 = np.copy(points[0])
    p_k3 = np.copy(points[1])
    p_k4 = np.zeros(3, dtype=np.float32)
    if circular:
        p_k1[:] = points[-1,:]
        tan_k1[:] = p_k3 - p_k1
        tan_k1 *= strength
    else:
        p_k1[:] = points[0,:]
    cdef Py_ssize_t i = 1
    while i < num_points - 1:
        p_k4[:] = points[i+1,:]
        tan_k2[:] = p_k4 - p_k2
        tan_k2 *= strength
        for j in range(subdivs):
            out_coords[index,:] = cubic_hermite_interpolate(p_k2, tan_k1, p_k3, tan_k2, dt*j)
            index += 1
        p_k1[:] = p_k2[:]
        p_k2[:] = p_k3[:]
        p_k3[:] = p_k4[:]
        tan_k1[:] = tan_k2[:]
        i += 1
    if circular:
        p_k4[0] = points[0,0]
        p_k4[1] = points[0,1]
        p_k4[2] = points[1,0]
        tan_k1 = p_k4 - p_k2
        tan_k1 *= strength
    else:
        tan_k1[:] = [0,0,0]
    for j in range(subdivs):
        out_coords[index,:] = cubic_hermite_interpolate(p_k2, tan_k1, p_k3, tan_k2, dt*j)
        index += 1
    if not circular:
        out_coords[index] = points[-1]
        return out_coords
    p_k1[:] = p_k2[:]
    p_k2[:] = p_k3[:]
    p_k3[:] = p_k4[:]
    tan_k1[:] = tan_k2[:]
    p_k4[:] = points[1,:]
    tan_k1 = p_k4 - p_k2
    tan_k1 *= strength
    for j in range(subdivs):
        out_coords[index,:] = cubic_hermite_interpolate(p_k2, tan_k1, p_k3, tan_k2, dt*j)
        index += 1
    return out_coords

cpdef float[:,:] get_rotmat3f(float angle, float[:] dir_vec):
    assert(np.linalg.norm(dir_vec)>0.0)
    cdef float x = dir_vec[0]
    cdef float y = dir_vec[1]
    cdef float z = dir_vec[2]
    cdef float c = np.cos(angle)
    cdef float s = np.sin(angle)
    rot_matrix = np.identity(3, dtype=np.float32)
    rot_matrix[0,0] = x*x*(1-c)+c
    rot_matrix[1,0] = y*x*(1-c)+z*s
    rot_matrix[2,0] = x*z*(1-c)-y*s
    rot_matrix[0,1] = x*y*(1-c)-z*s
    rot_matrix[1,1] = y*y*(1-c)+c
    rot_matrix[2,1] = y*z*(1-c)+x*s
    rot_matrix[0,2] = x*z*(1-c)+y*s
    rot_matrix[1,2] = y*z*(1-c)-x*s
    rot_matrix[2,2] = z*z*(1-c)+c
    return rot_matrix

cpdef tuple get_coil(float[:,:] spline, float coil_rad=0.2, float[:] color=None):
    if color is None:
        color = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    coil_points = np.array([[ 0.5, 0.866, 0.0], [ 1.0, 0.000, 0.0],
                            [ 0.5,-0.866, 0.0], [-0.5,-0.866, 0.0],
                            [-1.0, 0.000, 0.0], [-0.5, 0.866, 0.0]], dtype=np.float32)
    coil_points *= coil_rad
    coords = np.empty([spline.shape[0]*6, 3], dtype=np.float32)
    normals = np.empty([spline.shape[0]*6, 3], dtype=np.float32)
    colors = np.tile(color, coords.shape[0]).reshape(coords.shape).astype(np.float32)
    cdef Py_ssize_t i = 0
    dir_vec = np.empty(3, dtype=np.float32)
    for i in range(spline.shape[0] - 1):
        dir_vec[0] = spline[i+1][0] - spline[i][0]
        dir_vec[1] = spline[i+1][1] - spline[i][1]
        dir_vec[2] = spline[i+1][2] - spline[i][2]
        dir_vec /= np.linalg.norm(dir_vec)
        align_vec = np.cross([0.0, 0.0, 1.0], dir_vec).astype(np.float32)
        align_vec /= np.linalg.norm(align_vec)
        angle = np.arccos(np.dot([0.0, 0.0, 1.0], dir_vec))
        rot_mat = get_rotmat3f(angle, align_vec)
        for j, point in enumerate(coil_points):
            coords[i*6+j,:] = np.matmul(rot_mat, point) + spline[i]
            normals[i*6+j,:] = coords[i*6+j,:] - spline[i]
    for i, point in enumerate(coil_points):
        coords[-6+i,:] = np.matmul(rot_mat, point) + spline[-1]
        normals[-6+i,:] = coords[-6+i,:] - spline[-1]
    return coords, normals, colors

cpdef bezier_curve(p1, p2, p3, bezier_detail):
    points_mat = np.array([p1, p2, p3], dtype=np.float32)
    points = np.zeros([bezier_detail, 3], dtype=np.float32)
    for i, t in enumerate(np.linspace(0, 1, bezier_detail)):
        vec_t = np.array([(1-t)*(1-t), 2*t-2*t*t, t*t], dtype=np.float32)
        points[i,:] = np.matmul(vec_t, points_mat)
    return points

cpdef tuple get_strand(orig_spline, spline_detail, strand_ups, strand_rad=0.5, color=None):
    if color is None:
        color = np.array([1.0, 1.0, 0.0], dtype=np.float32)
    p1 = orig_spline[0]
    p2 = np.zeros(3, dtype=np.float32)
    for i in range(0, orig_spline.shape[0], spline_detail):
        p2 += orig_spline[i]
    p2 /= (orig_spline.shape[0]/spline_detail)
    p3 = orig_spline[-1]
    # For the beta strand, we don't use the catmull_rom_spline curve, but instead
    # a bezier curve, since I think it will look better
    spline = bezier_curve(p1, p2, p3, orig_spline.shape[0])
    coords = np.empty([spline.shape[0]*6, 3], dtype=np.float32)
    normals = np.empty([spline.shape[0]*6, 3], dtype=np.float32)
    colors = np.tile(color, coords.shape[0]).reshape(coords.shape).astype(np.float32)
    # Caclulate the angle between the first and second normals of the strand,
    # then create a rotation matrix to update the points and twist the strand
    angle = np.arccos(np.dot(strand_ups[0], strand_ups[1])) / (spline.shape[0]-spline_detail-1)
    align_vec = np.cross(strand_ups[0], strand_ups[1])
    align_vec /= np.linalg.norm(align_vec)
    rot_mat = get_rotmat3f(angle, align_vec)
    uv = np.array(strand_ups[0], dtype=np.float32)
    # bv: bezier vector - is the vector that points the direction of the spline
    # sv: side vector - is the vector that points to the side of the strand
    # uv: up vector - is the vector that points upwards of the strand
    for i in range(spline.shape[0] - spline_detail):
        bv = spline[i+1] - spline[i]
        bv /= np.linalg.norm(bv)
        sv = np.cross(bv, uv)
        sv /= np.linalg.norm(sv)
        coords[i*6]   = spline[i] + sv * strand_rad * 0.755
        coords[i*6+1] = spline[i] + sv * strand_rad * 0.75 - uv * strand_rad * .25
        coords[i*6+2] = spline[i] - sv * strand_rad * 0.75 - uv * strand_rad * .25
        coords[i*6+3] = spline[i] - sv * strand_rad * 0.755
        coords[i*6+4] = spline[i] - sv * strand_rad * 0.75 + uv * strand_rad * .25
        coords[i*6+5] = spline[i] + sv * strand_rad * 0.75 + uv * strand_rad * .25
        # We make a similar treatment to the normals as for the helix case,
        # however here is simplier since we have already one normal calculated,
        # the side vector :)
        v01 = coords[i*6+1] - coords[i*6]
        v23 = coords[i*6+3] - coords[i*6+2]
        n01 = np.cross(v01, bv)
        n23 = np.cross(v23, bv)
        n01 /= np.linalg.norm(n01)
        n23 /= np.linalg.norm(n23)
        n1 = (n01 - uv) / 2.0
        n1 /= np.linalg.norm(n1)
        n2 = (n23 - uv) / 2.0
        n2 /= np.linalg.norm(n2)
        normals[i*6]   = sv
        normals[i*6+1] = n1
        normals[i*6+2] = n2
        normals[i*6+3] = -sv
        normals[i*6+4] = -n1
        normals[i*6+5] = -n2
        # Now update the rotation of the up vector
        uv = np.matmul(rot_mat, uv)
    
    arrow_rads = np.linspace(strand_rad*2.5, 0.1, spline_detail)
    arros_inds = np.arange(spline.shape[0] - spline_detail, spline.shape[0], dtype=np.uint32)
    for i, r in zip(arros_inds, arrow_rads):
        if i < spline.shape[0] - 1:
            bv = spline[i+1] - spline[i]
            bv /= np.linalg.norm(bv)
        sv = np.cross(bv, uv)
        sv /= np.linalg.norm(sv)
        coords[i*6]   = spline[i] + sv * r * 0.755
        coords[i*6+1] = spline[i] + sv * r * 0.75 - uv * strand_rad * .25
        coords[i*6+2] = spline[i] - sv * r * 0.75 - uv * strand_rad * .25
        coords[i*6+3] = spline[i] - sv * r * 0.755
        coords[i*6+4] = spline[i] - sv * r * 0.75 + uv * strand_rad * .25
        coords[i*6+5] = spline[i] + sv * r * 0.75 + uv * strand_rad * .25
        # Now the normals
        v01 = coords[i*6+1] - coords[i*6]
        v23 = coords[i*6+3] - coords[i*6+2]
        n01 = np.cross(v01, bv)
        n23 = np.cross(v23, bv)
        n01 /= np.linalg.norm(n01)
        n23 /= np.linalg.norm(n23)
        n1 = (n01 - uv) / 2.0
        n1 /= np.linalg.norm(n1)
        n2 = (n23 - uv) / 2.0
        n2 /= np.linalg.norm(n2)
        normals[i*6]   = sv
        normals[i*6+1] = n1
        normals[i*6+2] = n2
        normals[i*6+3] = -sv
        normals[i*6+4] = -n1
        normals[i*6+5] = -n2
    return coords, normals, colors

cpdef get_helix_vector(p1, p2, p3, p4):
    com1234 = (p1 + p2 + p3 + p4) / 4.0
    com12 = (p1 + p2) / 2.0
    com23 = (p2 + p3) / 2.0
    com34 = (p3 + p4) / 2.0
    vec1 = com23 - com1234
    vec2 = com34 - com1234
    vec3 = np.cross(vec1, vec2)
    vec3 /= np.linalg.norm(vec3)
    pointA = com1234 + vec3 * np.linalg.norm(com34-com1234)
    pointB = com1234 - vec3 * np.linalg.norm(com34-com1234)
    com12B = (com12 + pointB) / 2.0
    com34A = (com34 + pointA) / 2.0
    dir_vec = com34A - com12B
    return dir_vec / np.linalg.norm(dir_vec)

cpdef tuple get_helix(spline, spline_detail, helix_rad=0.2, color=None):
    if color is None:
        color = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    coords = np.empty([spline.shape[0]*6, 3], dtype=np.float32)
    normals = np.empty([spline.shape[0]*6, 3], dtype=np.float32)
    colors = np.tile(color, coords.shape[0]).reshape(coords.shape).astype(np.float32)
    helix_vec = np.zeros(3, dtype=np.float32)
    for i in range(spline.shape[0] - spline_detail*3):
        # First calculate the vector with the main helix axis
        helix_vec += get_helix_vector(spline[i], spline[i+spline_detail],
                 spline[i+spline_detail*2], spline[i+spline_detail*3])
        helix_vec /= np.linalg.norm(helix_vec)
        spline_vec = spline[i+1] - spline[i]
        # The thickness_vec is how "fat" the helix will be. It always points
        # outside of the helix, it can be seen as the normal of a cylinder
        thickness_vec = np.cross(spline_vec, helix_vec)
        thickness_vec /= np.linalg.norm(thickness_vec)
        # Now we can calculate the points of the helix
        coords[i*6]   = spline[i] + helix_vec - thickness_vec * helix_rad / 2.0
        coords[i*6+1] = spline[i] - thickness_vec * helix_rad
        coords[i*6+2] = spline[i] - helix_vec - thickness_vec * helix_rad / 2.0
        coords[i*6+3] = spline[i] - helix_vec + thickness_vec * helix_rad / 2.0
        coords[i*6+4] = spline[i] + thickness_vec * helix_rad
        coords[i*6+5] = spline[i] + helix_vec + thickness_vec * helix_rad / 2.0
        # To calculate the normals, it gets tricky because the normals have to be
        # averaged. However, the good thing is that we only need to calculate
        # the normals for the half of the helix, the other half has to be same
        # but with opposite sign :)
        v01 = coords[i*6+1] - coords[i*6]
        v12 = coords[i*6+2] - coords[i*6+1]
        n01 = np.cross(spline_vec, v01)
        n12 = np.cross(spline_vec, v12)
        n01 /= np.linalg.norm(n01)
        n12 /= np.linalg.norm(n12)
        spline_vec /= np.linalg.norm(spline_vec)
        n0 = (helix_vec + n01) / 2.0
        n0 /= np.linalg.norm(n0)
        n1 = (n01 + n12) / 2.0
        n1 /= np.linalg.norm(n1)
        n2 = (n12 - helix_vec) / 2.0
        n2 /= np.linalg.norm(n2)
        normals[i*6]   = n0
        normals[i*6+1] = n1
        normals[i*6+2] = n2
        normals[i*6+3] = -n0
        normals[i*6+4] = -n1
        normals[i*6+5] = -n2
    # For the last pieces of the helix we don't have enough points to calculate
    # all the necessary vectors, so we just repeat the last ones used
    for i in range(spline.shape[0] - spline_detail*3, spline.shape[0]):
        if i < spline.shape[0] - 1:
            spline_vec = spline[i+1] - spline[i]
            thickness_vec = np.cross(spline_vec, helix_vec)
            thickness_vec /= np.linalg.norm(thickness_vec)
        coords[i*6] = spline[i] + helix_vec - thickness_vec * helix_rad / 2.0
        coords[i*6+1] = spline[i] - thickness_vec * helix_rad
        coords[i*6+2] = spline[i] - helix_vec - thickness_vec * helix_rad / 2.0
        coords[i*6+3] = spline[i] - helix_vec + thickness_vec * helix_rad / 2.0
        coords[i*6+4] = spline[i] + thickness_vec * helix_rad
        coords[i*6+5] = spline[i] + helix_vec + thickness_vec * helix_rad / 2.0
        # Same thing for normals
        v01 = coords[i*6+1] - coords[i*6]
        v12 = coords[i*6+2] - coords[i*6+1]
        n01 = np.cross(spline_vec, v01)
        n12 = np.cross(spline_vec, v12)
        n01 /= np.linalg.norm(n01)
        n12 /= np.linalg.norm(n12)
        spline_vec /= np.linalg.norm(spline_vec)
        n0 = (helix_vec + n01) / 2.0
        n0 /= np.linalg.norm(n0)
        n1 = (n01 + n12) / 2.0
        n1 /= np.linalg.norm(n1)
        n2 = (n12 - helix_vec) / 2.0
        n2 /= np.linalg.norm(n2)
        normals[i*6]   = n0
        normals[i*6+1] = n1
        normals[i*6+2] = n2
        normals[i*6+3] = -n0
        normals[i*6+4] = -n1
        normals[i*6+5] = -n2
    return coords, normals, colors

cpdef list get_indexes(num_points, points_perring, offset):
    # Add indices for the initial cap
    size_i = ((num_points//points_perring)-1)*2*6*3 + 2*4*3
    indexes = np.empty(size_i, dtype=np.uint32)
    indexes[:12] = [0,2,1, 2,4,3, 4,0,5, 0,4,2]
    i = 12
    for r in range(num_points//points_perring-1):
        for p in range(points_perring-1):
            indexes[i] = r*points_perring+p
            indexes[i+1] = r*points_perring+p+1
            indexes[i+2] = (r+1)*points_perring+p
            i += 3
        indexes[i] = (r+1)*points_perring - 1
        indexes[i+1] = r*points_perring
        indexes[i+2] = (r+2)*points_perring - 1
        i += 3
        for p in range(points_perring-1):
            indexes[i] = (r+1)*points_perring+p
            indexes[i+1] = r*points_perring+p+1
            indexes[i+2] = (r+1)*points_perring+p+1
            i += 3
        indexes[i] = (r+2)*points_perring - 1
        indexes[i+1] = r*points_perring
        indexes[i+2] = (r+1)*points_perring
        i += 3
    a = num_points - points_perring
    indexes[-12:] = [a,a+2,a+1, a+2,a+4,a+3, a+4,a,a+5, a,a+4,a+2]
    indexes += offset
    return indexes.tolist()

cpdef get_strand_normals(float[:,:] bbone, Py_ssize_t strand_start, Py_ssize_t strand_end):
    # cdef np.array ca1, co1, o1, ca2, co2, o2
    # cdef np.array v1a, v1b, v2a, v2b, n1, n2, n3
    ca1 = bbone[strand_start * 4 + 1]
    co1 = bbone[strand_start * 4 + 2]
    o1 = bbone[strand_start * 4 + 3]
    ca2 = bbone[strand_end * 4 + 1]
    co2 = bbone[strand_end * 4 + 2]
    o2 = bbone[strand_end * 4 + 3]
    v1a = ca1 - co1
    v1b = o1 - co1
    v2a = ca2 - co2
    v2b = o2 - co2
    n1 = np.cross(v1a, v1b)
    n2 = np.cross(v2a, v2b)
    n1 /= np.linalg.norm(n1)
    n2 /= np.linalg.norm(n2)
    if np.dot(n1,n2) < 0.0:
        n2 *= -1
    n3 = (n1 + n2) / 2
    n3 /= np.linalg.norm(n3)
    return n1, n2, n3

cpdef cartoon(float[:,:] bbone, float[:,:] calphas, list ss_assigned=None, int spline_detail=3,
              float coil_rad=0.2, float helix_rad=0.2, float strand_rad=0.8, float spline_strength=0.9):
    cdef Py_ssize_t sd = spline_detail
    spline = catmull_rom_spline(np.copy(calphas), calphas.shape[0], sd, strength=spline_strength)
    spline = np.array(spline, dtype=np.float32)
    
    cdef list coords = []
    cdef list normals = []
    cdef list colors = []
    cdef list indexes = []
    cdef int offset = 0
    
    for ss in ss_assigned:
        if ss[0] == 0:
            if ss[1] == 0:
                if ss[2] == calphas.shape[0]:
                    _crds, _nrmls, _cols = get_coil(spline[ss[1]*sd:ss[2]*sd], coil_rad=coil_rad)
                else:
                    _crds, _nrmls, _cols = get_coil(spline[ss[1]*sd:ss[2]*sd+1], coil_rad=coil_rad)
            else:
                if ss[2] == calphas.shape[0]:
                    _crds, _nrmls, _cols = get_coil(spline[ss[1]*sd-1:ss[2]*sd], coil_rad=coil_rad)
                else:
                    _crds, _nrmls, _cols = get_coil(spline[ss[1]*sd-1:ss[2]*sd+1], coil_rad=coil_rad)
            
            _inds = get_indexes(_crds.shape[0], 6, offset)
            offset += _crds.shape[0]
            indexes.extend(_inds)
            coords.extend(_crds)
            normals.extend(_nrmls)
            colors.extend(_cols)
        elif ss[0] == 1:
            _crds, _nrmls, _cols = get_helix(spline[ss[1]*sd:ss[2]*sd], sd, helix_rad=helix_rad)
            _inds = get_indexes(_crds.shape[0], 6, offset)
            offset += _crds.shape[0]
            indexes.extend(_inds)
            coords.extend(_crds)
            normals.extend(_nrmls)
            colors.extend(_cols)
        elif ss[0] == 2:
            _crds, _nrmls, _cols = get_strand(spline[ss[1]*sd:ss[2]*sd], sd, ss[3], strand_rad=strand_rad)
            _inds = get_indexes(_crds.shape[0], 6, offset)
            offset += _crds.shape[0]
            indexes.extend(_inds)
            coords.extend(_crds)
            normals.extend(_nrmls)
            colors.extend(_cols)
    out_coords = np.array(coords, dtype=np.float32)
    out_normals = np.array(normals, dtype=np.float32)
    out_colors = np.array(colors, dtype=np.float32)
    out_indexes = np.array(indexes, dtype=np.uint32)
    print("lengths:")
    print(spline.shape, out_coords.shape, out_normals.shape, out_colors.shape, out_indexes.shape)
    return out_coords, out_normals, out_indexes, out_colors

cpdef ribbon(float[:,:] calphas, int spline_detail=3, float spline_strength=0.9):
    spline = catmull_rom_spline(np.copy(calphas), calphas.shape[0], spline_detail, strength=spline_strength)
    return np.array(spline, dtype=np.float32)



'''

def make_normals(coords, indexes):
    # normals = np.empty([indexes.shape[0], 3], dtype=np.float32)
    normals = []
    for i in range(0, indexes.shape[0], 3):
        vec1 = coords[indexes[i+1]] - coords[indexes[i]]
        vec2 = coords[indexes[i+2]] - coords[indexes[i+1]]
        normal = np.cross(vec2, vec1)
        normal /= np.linalg.norm(normal)
        normals.append(normal)
        normals.append(normal)
        normals.append(normal)
        # normals[indexes[i]][:] = normal
        # normals[indexes[i+1]][:] = normal
        # normals[indexes[i+2]][:] = normal
    return normals

def get_strand_vectors(p1, p2, p3):
    com123 = (p1 + p2 + p3) / 3.0
    com12 = (p1 - p2) / 2.0
    com23 = (p2 - p3) / 2.0
    vec1 = com123 - com12
    vec1 /= np.linalg.norm(vec1)
    vec2 = com123 - com23
    vec2 /= np.linalg.norm(vec2)
    up_vec = vec1 + vec2
    up_vec /= np.linalg.norm(up_vec)
    vec3 = p3 - p1
    side_vec = np.cross(up_vec, vec3)
    side_vec /= np.linalg.norm(side_vec)
    return up_vec, side_vec

# def calculate_secondary_structure(visObj):
#     """
#         First, the distances d2i, d3i and d4i between the (i - 1)th
#         residue and the (i + 1)th, the (i + 2)th and the (i + 3)th,
#         respectively, are computed from the cartesian coordinates
#         of the Ca carbons, as well as the angle ti and dihedral angle
#         ai defined by the Ca carbon triplet (i - 1, i , i + 1) and
#         quadruplet (i - 1, i, i + 1, i + 2), respectively.
        
        
#         Assignment parameters
#                                    Secondary structure
                                   
#                                    Helix        Strand
                                   
#         Angle T (°)               89 ± 12       124 ± 14
#         Dihedral angle a (°)      50 ± 20      -170 ± 4 5
                                               
#         Distance d2 (A)           5.5 ± 0.5    6.7 ± 0.6
#         Distance d3 (A)           5.3 ± 0.5    9.9 ± 0.9
#         Distance d4 (A)           6.4 ± 0.6    12.4 ± 1.1


#     """
#     if visObj.c_alpha_bonds == [] or visObj.c_alpha_atoms == []:
#         visObj.get_backbone_indexes()
    
#     for atom in visObj.c_alpha_atoms:
#         print(atom.index, atom.name, atom.bonds_indexes, atom.bonds)
    

#     size = len(visObj.c_alpha_bonds)
#     SSE_list  = "C"
#     SSE_list2 = []
    
    
#     block     = [0,0,1]
#     SS_before = 1
#     for i in range(1,size -2):
        
#         CA0 = visObj.c_alpha_bonds[i-1].atom_i # i - 1
#         CA1 = visObj.c_alpha_bonds[i-1].atom_j # i
        
#         CA2 = visObj.c_alpha_bonds[i].atom_i   # i
#         CA3 = visObj.c_alpha_bonds[i].atom_j   # i + 1
                                               
#         CA4 = visObj.c_alpha_bonds[i+1].atom_i # i + 1
#         CA5 = visObj.c_alpha_bonds[i+1].atom_j # i + 2
                                               
#         CA6 = visObj.c_alpha_bonds[i+2].atom_i # i + 2
#         CA7 = visObj.c_alpha_bonds[i+2].atom_j # i + 3
                                               
#         #CA8 = visObj.c_alpha_bonds[i+3].atom_i # i + 3 
#         #CA9 = visObj.c_alpha_bonds[i+3].atom_j #


#         if CA1 == CA2 and CA3 == CA4 and CA5 == CA6:
#             #print ("CA1 = CA2")
            
#             # distances
#             d2i  = CA0.coords(), CA3.coords()
#             d2i  = np.linalg.norm(d2i)
            
#             d3i  = CA0.coords(), CA5.coords()
#             d3i  = np.linalg.norm(d3i)
            
#             d4i  = CA0.coords(), CA7.coords()
#             d4i  = np.linalg.norm(d4i)
            
#             # angle
#             v0   = CA1.coords(),CA0.coords()
#             v1   = CA1.coords(), CA3.coords()
            
#             ti   = 57.295779513*(mop.angle(v0, v1))
            
#             # dihedral 
#             ai   = 57.295779513*(mop.dihedral(CA0.coords(), CA1.coords(), CA3.coords(), CA5.coords()))
            
            
            
#             SS = None
#             SS_char = None
            
#             if 77.0 <= ti <= 101 and 30 <= ai <= 70:
#                 #print(CA1.resi, CA1.name, CA1.resn, CA1.name, "H", d2i, d3i, d4i, ti,  ai)
#                 SS = 1
#                 SS_char = "H"

#             elif 5.0 <= d2i <= 6.0 and 4.8 <= d3i <= 5.8 and 5.8 <= d4i <= 7.0:
#                 SS = 1
#                 SS_char = "H"
            
#             elif 110.0 <= ti <= 138 and -215 <= ai <= -125:
#                 SS = 2
#                 SS_char = "S"
            
#             elif 6.1 <= d2i <= 7.3 and 9.0 <= d3i <= 10.8 and 11.3 <= d4i <= 13.5:
#                 SS = 1
#                 SS_char = "S"
            
#             """
#             if 5.0 <= d2i <= 6.0:
#                 #print("d2i", d2i)
                
#                 if 4.8 <= d3i <= 5.8:
#                     #print("d3i", d3i)

#                     if 5.8 <= d4i <= 7.0:
#                         #print("d4i", d4i)

#                         if 77.0 <= ti <= 101:
                            
#                             if 30 <= ai <= 70:
#                                 print(CA1.resi, CA1.name, CA1.resn, CA1.name, "H", d2i, d3i, d4i, ti,  ai)
#                                 SS = "H"
      
                     
#             if 6.1 <= d2i <= 7.3:
#                 #print("d2i", d2i)
                
#                 if 9.0 <= d3i <= 10.8:
#                     #print("d3i", d3i)

#                     if 11.3 <= d4i <= 13.5:
#                         #print("d4i", d4i)

#                         if 110.0 <= ti <= 138:
#                             if -215 <= ai <= -125:
#                                 print(CA1.resi, CA1.name, CA1.resn, CA1.name, "S", d2i, d3i, d4i, ti,  ai)
#                                 SS = "S"
#             """
            
#             if SS:
#                 pass
#             else:
#                 SS = 0 
#                 SS_char = "C"
#             print(CA1.resi, CA1.name, CA1.resn, CA1.name, SS, d2i, d3i, d4i, ti,  ai)
            
#             SSE_list += SS_char

            
#     SSE_list += "CCC"
#     print(SSE_list, len(SSE_list))
#     SSE_list = SSE_list.replace("CHCHC",  "CCCC")
#     SSE_list = SSE_list.replace("CHC",  "CCC")
#     SSE_list = SSE_list.replace("HCH",  "HHH")
#     SSE_list = SSE_list.replace("CHS",  "CCS")

#     SSE_list = SSE_list.replace("CHHC", "CCCC")
#     SSE_list = SSE_list.replace("CSSC", "CCCC")
#     SSE_list = SSE_list.replace("CSC",  "CCC")
#     SSE_list = SSE_list.replace("HSH",  "HHH")
#     SSE_list = SSE_list.replace("SHS",  "SSS")
#     SSE_list = SSE_list.replace("CHSC",  "CCCC")
#     print(SSE_list, len(SSE_list))
    
    
#     SSE_list2     = []
#     block         = [0,0,0]
#     SS_before     = "C"
    
#     counter = 1
#     for SS in SSE_list:
        
#         if SS == SS_before:
#             block[2] += 1
#         else:
#             SSE_list2.append(block)
#             SS_before = SS
#             print (block)
            
#             if SS == "C":
#                 SS_code = 0
            
#             elif SS == "H":
#                 SS_code = 1
            
#             else:
#                 SS_code = 2    
            
#             block = [SS_code, counter-1, counter]
            
#         counter += 1
#     SSE_list2.append(block)
#     print(SSE_list2)
#     return SSE_list2 

'''