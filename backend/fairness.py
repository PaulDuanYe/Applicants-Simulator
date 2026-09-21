"""Validate participant opinions, never infer fairness from outcomes."""
OPTIONS = {'age_discrimination', 'gender_discrimination', 'experience_overemphasis',
           'education_overemphasis', 'skills_overemphasis', 'other', 'none', 'unsure'}


def validate_feedback(data, outcomes):
    def check(condition, message):
        if not condition:
            raise ValueError(message)

    def prose(key, source=data):
        value = source.get(key)
        check(isinstance(value, str) and 0 < len(value.strip()) <= 5000, '请填写理由或说明（最多 5000 字）。')
        return value.strip()

    rating = data.get('fairness_rating')
    check(type(rating) is int and 1 <= rating <= 10, '请选择 1–10 的公平评分。')
    options = data.get('group_selections')
    check(type(options) is list and len(options) > 0 and all(type(o) is str and o in OPTIONS for o in options), '请至少选择一项你对整体结果的看法。')
    check(len(set(options)) == len(options) and (not set(options) & {'none', 'unsure'} or len(options) == 1), '选项不能重复；“没有上述问题”和“不确定”不能与其他选项同时选择。')
    group_reason = prose('group_reason')
    other = prose('other_group_view') if 'other' in options else None
    choice = data.get('individual_comparison')
    check(choice in ('yes', 'no', 'unsure'), '请选择“有”“没有”或“不确定”。')
    comparisons = []
    if choice == 'yes':
        rows = data.get('comparisons')
        check(type(rows) is list and 1 <= len(rows) <= 9, '请添加 1–9 组比较。')
        seen = set()
        for row in rows:
            check(type(row) is dict, '比较格式无效。')
            rejected, passed = row.get('rejected_profile_id'), row.get('passed_profile_id')
            check(type(rejected) is str and type(passed) is str, '请选择比较的申请者。')
            check(outcomes.get(rejected) == 'reject' and outcomes.get(passed) == 'pass', '每组请选择一位未通过者和一位已通过者。')
            check((rejected, passed) not in seen, '这两个人已经比较过了，请删除重复的一组。')
            seen.add((rejected, passed))
            comparisons.append((rejected, passed, prose('reason', row)))
    individual_reason = prose('individual_reason') if choice != 'yes' else None
    return rating, options, group_reason, other, choice, individual_reason, comparisons
