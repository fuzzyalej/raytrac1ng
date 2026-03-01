// Basic test scene — three spheres on a ground plane

camera {
  location <0, 2, -5>
  look_at <0, 0.5, 0>
  fov 60
}

light {
  position <5, 10, -3>
}

// Ground
plane {
  normal <0, 1, 0>
  offset 0
}

// Center sphere
sphere {
  center <0, 1, 0>
  radius 1.0
}

// Left sphere (smaller)
sphere {
  center <-2.2, 0.6, 2>
  radius 0.6
}

// Right sphere (medium)
sphere {
  center <1.8, 0.8, -2>
  radius 0.8
}
