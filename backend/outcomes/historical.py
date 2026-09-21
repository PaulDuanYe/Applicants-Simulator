"""Historical-only inputs are independent of the shared applicant contract."""


def generate_historical(applicants, historical_inputs):
    if historical_inputs is None:
        raise ValueError('Historical source snapshots are required.')
    results = {}
    for applicant in historical_inputs:
        profile_id, decision = applicant['profile_id'], applicant['source_decision']
        if profile_id in results or decision not in ('pass', 'reject'):
            raise ValueError('Historical records contain duplicate profiles or invalid decisions.')
        results[profile_id] = decision
    if set(results) != {a['profile_id'] for a in applicants}:
        raise ValueError('Historical snapshots do not match the applicant group.')
    return results
