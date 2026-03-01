// 08-shapes.pov — Showcase of Box, Cylinder, Cone, and Torus primitives

camera  { location <0,6,-18>  look_at <0,1,0>  fov 45 }
light   { position <10,20,-5> }

// Ground plane
plane   { normal <0,1,0>  offset -0.1  color gray }

// Box (AABB) — left
box {
    min <-6,0,-2>  max <-3.5,2.5,1>
    color red
    reflect 0.1
}

// Cylinder — centre-left
cylinder {
    bottom <-1.5,0,-1>  top <-1.5,3,-1>  radius 0.8
    color blue
}

// Cone (true cone) — centre-right
cone {
    bottom <1.5,0,-1>  top <1.5,3,-1>
    bottom_radius 1.0  top_radius 0.0
    color green
}

// Torus — right
torus {
    center <5,1.5,0>  axis <0,1,0>
    major_radius 1.3  minor_radius 0.45
    color yellow
    reflect 0.2
}
