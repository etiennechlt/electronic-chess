// Drawing helpers shared by the scenes. Pure functions of their arguments:
// the same call gives the same path on every frame and every render.
window.FILM = {
  // A struck resonator: a sine under an exponential envelope, from x0 to x1,
  // as an SVG path. `cycles` over the whole span, envelope e^(-u * decay).
  ringdownPath: function (x0, x1, yMid, amp, cycles, decay, steps) {
    var n = steps || 800;
    var d = "";
    for (var i = 0; i <= n; i++) {
      var u = i / n;
      var x = x0 + (x1 - x0) * u;
      var y = yMid - amp * Math.exp(-u * decay) * Math.sin(2 * Math.PI * cycles * u);
      d += (i ? " L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
    }
    return d;
  },

  // The envelope alone, upper (sign 1) or lower (sign -1).
  envelopePath: function (x0, x1, yMid, amp, decay, sign, steps) {
    var n = steps || 60;
    var d = "";
    for (var i = 0; i <= n; i++) {
      var u = i / n;
      var y = yMid - sign * amp * Math.exp(-u * decay);
      d += (i ? " L" : "M") + (x0 + (x1 - x0) * u).toFixed(1) + " " + y.toFixed(1);
    }
    return d;
  },

  // Frequency axis of scenes 06 and 07: kHz to a y coordinate, low at the bottom.
  freqY: function (khz) {
    return 820 - ((khz - 200) / 450) * 800;
  },

  // Prepare a path for a left-to-right draw: returns its length.
  dashReady: function (path) {
    var len = path.getTotalLength();
    path.style.strokeDasharray = len + " " + len;
    path.style.strokeDashoffset = len;
    return len;
  },
};
