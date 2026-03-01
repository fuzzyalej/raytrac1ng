// 07-refractions.pov — Glass spheres demonstrating Snell's law + Fresnel

camera {
    location <0, 1.5, -6>
    look_at  <0, 0, 0>
    fov 45
}

light {
    position <6, 10, -4>
    radius 1.5
    samples 16
}

// Ground plane
plane {
    normal <0, 1, 0>
    offset -1.2
    color <0.7, 0.7, 0.65>
    reflect 0.1
}

// Back wall
plane {
    normal <0, 0, -1>
    offset -5
    color <0.4, 0.55, 0.8>
}

// Large glass sphere (ior 1.5 — borosilicate glass)
sphere {
    center <0, 0, 0>
    radius 1.2
    color white
    opacity 0.0
    ior 1.5
}

// Coloured reference spheres visible through the glass
sphere {
    center <-2.5, 0, 3>
    radius 0.8
    color <0.9, 0.15, 0.1>
}

sphere {
    center <2.5, 0, 3>
    radius 0.8
    color <0.1, 0.3, 0.9>
}

sphere {
    center <0, 0, 3.5>
    radius 0.8
    color <0.1, 0.8, 0.2>
}
