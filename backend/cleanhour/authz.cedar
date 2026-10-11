// Who may do what in CleanHour. Identity comes from Amazon Cognito (ID token claims);
// these Cedar policies decide authority on every protected request.

// A principal runs their own school, and is the only one who can approve what children do.
@id("principal_runs_own_school")
permit(principal in Role::"principal",
       action in [Action::"ViewPlan", Action::"RunPlan", Action::"Approve", Action::"SetGrap", Action::"Ask"],
       resource)
when { principal.school == resource.school };

// Teachers see their school's plan and can ask questions, but cannot change or approve it.
@id("teacher_reads_own_school")
permit(principal in Role::"teacher", action in [Action::"ViewPlan", Action::"Ask"], resource)
when { principal.school == resource.school };

// A district admin (e.g. DoE) onboards schools and can see and re-run any school's plan.
@id("district_admin")
permit(principal in Role::"admin",
       action in [Action::"ViewPlan", Action::"RunPlan", Action::"SetGrap", Action::"Ask", Action::"CreateSchool"],
       resource);

// Approval stays with the school: not even an admin approves on a principal's behalf.
@id("only_principals_approve")
forbid(principal, action == Action::"Approve", resource)
unless { principal in Role::"principal" };
