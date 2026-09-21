"""Resolve the existing case rule separately from outcome retrieval."""


def resolve_case_outcomes(applicants, method_results, alternative_job):
    if len(applicants) != 6 or len({a['profile_id'] for a in applicants}) != 6:
        raise ValueError('Expected six unique applicants.')
    if set(method_results) != {a['profile_id'] for a in applicants}:
        raise ValueError('Method results do not match the saved applicants.')
    if sum(a['applicant_role'] == 'participant' for a in applicants) != 1:
        raise ValueError('Expected one participant.')
    results = []
    for applicant in applicants:
        decision = method_results[applicant['profile_id']]
        override = alternative_job and applicant['applicant_role'] == 'participant'
        final = 'reject' if override else decision
        rule = 'alternative_job_rejection' if override else None
        if decision not in ('pass', 'reject'):
            raise ValueError('Invalid method outcome.')
        results.append((applicant['profile_id'], final, rule))
    if sum(r[1] == 'pass' for r in results) != 3:
        raise ValueError('Final outcomes must contain three pass and three reject decisions.')
    return results
