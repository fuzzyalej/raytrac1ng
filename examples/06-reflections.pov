// 06-reflections.pov — showcase of mirror reflections

camera {
  location <0, 2, -7>
  look_at <0, 1, 0>
  fov 55
}

light {
  position <4, 8, -4>
  radius 1.0
  samples 16
}

// Slightly reflective ground
plane {
  normal <0, 1, 0>
  offset 0
  color gray
  reflect 0.4
}

// Perfect mirror sphere
sphere {
  center <-1.5, 1, 0>
  radius 1.0
  color white
  reflect 1.0
}

// Matte red sphere (gets reflected in the mirror)
sphere {
  center <1.5, 1, 0>
  radius 1.0
  color red
}

// Partial mirror blue sphere
sphere {
  center <0, 0.5, 2>
  radius 0.5
  color blue
  reflect 0.6
}
