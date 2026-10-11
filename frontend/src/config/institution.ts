export interface InstitutionConfig {
  name: string;
  code: string;
  academicYear: string;
  platformName: string;
  platformTagline: string;
  environmentBadge: string;
  isSimulated: boolean;
  supportEmail: string;
  supportPhone: string;
}

export const institutionConfig: InstitutionConfig = {
  name: "XYZ Engineering College",
  code: "XYZ",
  academicYear: "2026-27",
  platformName: "AdmissionAI",
  platformTagline: "AI-Driven Smart Admission Automation and Transparent Student Onboarding Platform",
  environmentBadge: "PROTOTYPE / DEMO ENVIRONMENT (M.Tech AI & Data Science)",
  isSimulated: true,
  supportEmail: "admissions-demo@xyz.edu.demo",
  supportPhone: "+91 (044) 2792-XXXX",
};
