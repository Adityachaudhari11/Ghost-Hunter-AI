/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
const config = {
  packageManager: "npm",
  reporters: ["html", "clear-text", "progress", "json"],
  testRunner: "jest",
  coverageAnalysis: "perTest",
  checkers: ["typescript"],
  tsconfigFile: "tsconfig.json",
  mutate: ["src/**/*.ts"],
  jsonReporter: {
    fileName: "reports/mutation/mutation.json"
  },
  thresholds: {
    high: 80,
    low: 60,
    break: null
  },
  concurrency: 4,
  timeoutMS: 10000,
  timeoutFactor: 1.5
};

export default config;
