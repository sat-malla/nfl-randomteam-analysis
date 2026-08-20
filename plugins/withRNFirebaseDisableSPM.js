const { withDangerousMod } = require('@expo/config-plugins');
const fs = require('fs');
const path = require('path');

module.exports = function withRNFirebaseDisableSPM(config) {
  return withDangerousMod(config, [
    'ios',
    async (config) => {
      const podfilePath = path.join(config.modRequest.platformProjectRoot, 'Podfile');
      let contents = fs.readFileSync(podfilePath, 'utf-8');
      if (!contents.includes('$RNFirebaseDisableSPM')) {
        contents = `$RNFirebaseDisableSPM = true\n` + contents;
        fs.writeFileSync(podfilePath, contents);
      }
      return config;
    },
  ]);
};