import sharedCases from "../../shared/demo_cases_v1.json";

export interface DemoCase {
  id: string;
  title: string;
  crop_code: string;
  crop_name: string;
  focus: string;
  query: string;
  expected_behavior: string;
}

export const demoCases = sharedCases as DemoCase[];
