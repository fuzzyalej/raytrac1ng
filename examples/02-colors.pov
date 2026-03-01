// 02-colors.pov — showcase of named colors
camera {
  location <0, 3, -7>
  look_at <0, 0.5, 0>
  fov 60
}

light {
  position <5, 10, -3>
}

plane {
  normal <0, 1, 0>
  offset 0
  color gray
}

// Center: red sphere
sphere {
  center <0, -1, 0>
  radius 2.0
  color red
}

// Left: blue sphere
sphere {
  center <-2.5, 0.7, 1>
  radius 0.7
  color blue
}

// Right: yellow sphere
sphere {
  center <2.5, 0.7, 1>
  radius 0.7
  color yellow
}

// Far left: green sphere
sphere {
  center <-1.5, 0.5, 3>
  radius 0.5
  color green
}

// Far right: magenta sphere
sphere {
  center <1.5, 0.5, 3>
  radius 0.5
  color magenta
}

// Back left: cyan sphere
sphere {
  center <-1.0, 0.4, -1>
  radius 0.4
  color cyan
}

// Back right: orange sphere
sphere {
  center <1.0, 0.4, -1>
  radius 0.4
  color orange
}
