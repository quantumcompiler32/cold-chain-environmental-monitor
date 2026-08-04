(function exposePhase1Inference(root) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = require('../web/scripts/vaccine-inference.js');
  } else {
    root.Phase1Inference = root.VaccineInference;
  }
})(typeof globalThis === 'undefined' ? this : globalThis);
