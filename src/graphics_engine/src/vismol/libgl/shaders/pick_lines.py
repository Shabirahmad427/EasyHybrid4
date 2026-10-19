#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Screen-space wide segments for the colour-ID picking pass.

The picking pass encodes atom IDs in line colours. It used to widen those
lines with glLineWidth(), but core-profile wide lines are deprecated and
macOS OpenGL clamps the line width to 1 pixel. A 1-pixel line endpoint at an
atom centre is not reliably rasterized, so clicks on lines/nonbonded/dashed
atoms missed on macOS. Geometry shaders that include this snippet emit each
segment as a triangle strip of an exact pixel width instead, which every
OpenGL 3.3 core driver rasterizes the same way.

Uniforms (set with Representation._load_pick_line_uniforms):
    u_viewport_size   -- render-target size in framebuffer pixels
    u_pick_line_width -- full segment width in framebuffer pixels
"""

WIDE_SEGMENT_GLSL = """
uniform vec2 u_viewport_size;
uniform float u_pick_line_width;

// Flat: atom IDs are exact colour bytes; never interpolate them.
flat out vec3 frag_color;

vec4 offset_clip_position(vec4 clip, vec2 offset_px){
    return clip + vec4(offset_px * 2.0 / u_viewport_size * clip.w, 0.0, 0.0);
}

void emit_wide_segment(vec4 a, vec4 b, vec3 color, bool cap_a, bool cap_b){
    // Clip against a plane just in front of the eye so the perspective
    // divide below is defined; the rasterizer clips the rest.
    const float near_w = 1e-4;
    if (a.w < near_w && b.w < near_w) {
        return;
    }
    if (a.w < near_w) {
        a = mix(a, b, (near_w - a.w) / (b.w - a.w));
        cap_a = false;
    } else if (b.w < near_w) {
        b = mix(b, a, (near_w - b.w) / (a.w - b.w));
        cap_b = false;
    }
    vec2 screen_a = a.xy / a.w * 0.5 * u_viewport_size;
    vec2 screen_b = b.xy / b.w * 0.5 * u_viewport_size;
    vec2 direction = screen_b - screen_a;
    float length_px = length(direction);
    direction = length_px > 1e-6 ? direction / length_px : vec2(1.0, 0.0);
    float half_width = 0.5 * max(u_pick_line_width, 1.0);
    vec2 normal = vec2(-direction.y, direction.x) * half_width;
    // Square caps extend past an atom endpoint so the atom's own centre
    // pixel is always inside its hit region.
    vec2 extend_a = cap_a ? -direction * half_width : vec2(0.0);
    vec2 extend_b = cap_b ? direction * half_width : vec2(0.0);

    frag_color = color;
    gl_Position = offset_clip_position(a, extend_a + normal);
    EmitVertex();
    frag_color = color;
    gl_Position = offset_clip_position(a, extend_a - normal);
    EmitVertex();
    frag_color = color;
    gl_Position = offset_clip_position(b, extend_b + normal);
    EmitVertex();
    frag_color = color;
    gl_Position = offset_clip_position(b, extend_b - normal);
    EmitVertex();
    EndPrimitive();
}
"""

FLAT_COLOR_FRAGMENT_SHADER = """
#version 330

flat in vec3 frag_color;

out vec4 final_color;

void main(){
    final_color = vec4(frag_color, 1.0);
}
"""
