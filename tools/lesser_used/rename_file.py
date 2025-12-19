# # rename_files.py
# import os
#
# # Directory containing your PDFs
# directory = r"C:\Users\drzon\OneDrive\Documents\1. Business and admin\1. AI Chatbot\MediTest docs\PDFs"
#
# # List of base filenames (without .pdf, we’ll check both states)
# files = [
#     "SOP-HR-001_Recruitment_Hiring_v1.0",
#     "SOP-HR-002_Onboarding_Orientation_v1.1",
#     "SOP-HR-003_Performance_Appraisals_v2.0",
#     "SOP-HR-004_Grievance_Disciplinary_v1.3",
#     "SOP-HR-005_Termination_Offboarding_v2.0",
#     "SOP-HR-006_RemoteWork_HybridPolicy_v1.0",
#     "SOP-HR-007_Benefits_Wellness_v1.2",
#     "SOP-HR-008_WorkplaceSafety_OccHealth_v2.0",
#     "SOP-HR-009_DEI_Policy_v1.1",
#     "SOP-HR-010_Training_Development_v2.0",
#     "SOP-HR-011_Travel_ExpenseReimbursement_v1.3",
#     "SOP-HR-012_CodeOfConduct_Ethics_v2.0",
#     "SOP-HR-013_ITSecurity_RemoteAccess_v1.1",
#     "SOP-HR-014_HarassmentPrevention_Reporting_v2.0",
#     "SOP-HR-015_ConflictOfInterest_Disclosure_v1.2",
#     "SOP-MA-001_HCPPayments_Engagements_v1.0",
#     "SOP-MA-002_IIS_Approval_v2.0",
#     "SOP-MA-003_MedComm_Interactions_v1.1",
#     "SOP-MA-004_MedInfo_Inquiries_v1.0",
#     "SOP-MA-005_AEReporting_PhVig_v2.1",
#     "SOP-MA-006_Scientific_Exchange_v1.2",
#     "SOP-MA-007_PromoMarketing_Compliance_v3.0",
#     "SOP-MA-008_Publication_ScientificDisclosure_v1.1",
#     "SOP-MA-009_CompassionateUse_ExpandedAccess_v2.0",
#     "SOP-MA-010_AdvisoryBoard_Management_v1.3",
#     "SOP-MA-011_PAG_Interactions_v1.0",
#     "SOP-MA-016_RWE_HealthOutcomes_v1.0",
#     "SOP-MA-017_ExpandedAccess_RareDiseases_v1.1",
#     "SOP-MA-018_MSL_FieldMedical_v2.0",
#     "SOP-MA-019_CompassionateUse_NamedPatient_v1.2",
#     "SOP-MKT-001_PromoMaterial_Approval_v1.0",
#     "SOP-MKT-002_Digital_SocialMedia_v1.1",
#     "SOP-MKT-003_HCP_Speaker_Sponsorship_v2.0",
#     "SOP-MKT-004_SalesRep_PromoConduct_v1.2",
#     "SOP-MKT-005_Congress_Exhibition_v1.0",
#     "SOP-MKT-006_MarketResearch_DataCollection_v1.0",
#     "SOP-MKT-007_PatientEducation_Materials_v1.1",
#     "SOP-MKT-008_Influencer_ThirdParty_v1.0",
#     "SOP-MKT-009_CoMarketing_JointVentures_v1.2",
#     "SOP-MKT-010_BrandStrategy_Competitive_v1.0",
#     "SOP-MKT-011_DiseaseAwareness_PublicHealth_v1.1",
#     "SOP-MKT-012_KOL_Engagement_FMV_v2.0",
#     "SOP-MKT-013_Tender_GovtContracting_v1.2",
#     "SOP-MKT-014_PricingStrategy_Competitive_v1.0",
#     "SOP-MKT-015_EventSponsorship_Conferences_v1.1"
# ]
#
# # Rename files to ensure .pdf extension, accounting for mixed states
# for base_name in files:
#     old_path_no_ext = os.path.join(directory, base_name)
#     old_path_with_ext = os.path.join(directory, f"{base_name}.pdf")
#     target_name = f"{base_name}.pdf"
#     target_path = os.path.join(directory, target_name)
#
#     # Case 1: File exists without .pdf
#     if os.path.exists(old_path_no_ext):
#         if not os.path.exists(target_path):  # Avoid overwriting if already renamed
#             try:
#                 os.rename(old_path_no_ext, target_path)
#                 print(f"Renamed: {base_name} -> {target_name}")
#             except PermissionError:
#                 print(f"Permission denied: {base_name} is in use. Close it and retry.")
#             except Exception as e:
#                 print(f"Error renaming {base_name}: {e}")
#         else:
#             print(f"Already renamed: {target_name} exists.")
#     # Case 2: File already has .pdf
#     elif os.path.exists(old_path_with_ext):
#         print(f"Already has .pdf: {base_name}.pdf - No action needed.")
#     # Case 3: File not found at all
#     else:
#         print(f"File not found: {base_name} (with or without .pdf)")
#
# print("\nRenaming complete. Check directory and resolve any permission issues.")