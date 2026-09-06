import { verifyProductionUi } from "./production-ui-contract";

async function main(): Promise<void> {
  const baseUrl = process.argv[2] ?? process.env.PRODUCTION_URL ?? "https://opendq-observatory.vercel.app";
  try {
    const result = await verifyProductionUi(baseUrl);
    console.log("PRODUCTION_UI=PASS");
    console.log(`BASE_URL=${result.baseUrl}`);
    console.log(`STYLESHEETS=${result.stylesheetCount}`);
    console.log(`REQUIRED_SELECTORS=${result.requiredSelectors.join(",")}`);
  } catch (error) {
    console.error("PRODUCTION_UI=FAIL");
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

void main();
