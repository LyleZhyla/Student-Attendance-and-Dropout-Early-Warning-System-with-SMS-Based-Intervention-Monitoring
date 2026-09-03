QUESTIONNAIRE_VERSION = 'support-check-in-v1-draft'
PRIVACY_NOTICE_VERSION = 'wellbeing-privacy-v1-draft'

SCALE_CHOICES = [
    {'value': 'NONE', 'label': 'None reported'},
    {'value': 'SOME', 'label': 'Some concern'},
    {'value': 'SIGNIFICANT', 'label': 'Significant concern'},
    {'value': 'PREFER_NOT_TO_SAY', 'label': 'Prefer not to say'},
]
CONNECTION_CHOICES = [
    {'value': 'STRONG', 'label': 'Strong'},
    {'value': 'OKAY', 'label': 'Okay'},
    {'value': 'LOW', 'label': 'Low'},
    {'value': 'PREFER_NOT_TO_SAY', 'label': 'Prefer not to say'},
]
ACCESS_CHOICES = [
    {'value': 'YES', 'label': 'Yes'},
    {'value': 'SOMETIMES', 'label': 'Sometimes'},
    {'value': 'NO', 'label': 'No'},
    {'value': 'PREFER_NOT_TO_SAY', 'label': 'Prefer not to say'},
]
TOPIC_CHOICES = [
    {'value': 'ACADEMIC', 'label': 'Academic support'},
    {'value': 'ATTENDANCE', 'label': 'Attendance support'},
    {'value': 'PEER', 'label': 'Peer relationships'},
    {'value': 'FAMILY', 'label': 'Family circumstances'},
    {'value': 'HEALTH_ACCESS', 'label': 'Access to health or well-being services'},
    {'value': 'TRANSPORTATION', 'label': 'Transportation'},
    {'value': 'FINANCIAL', 'label': 'Financial or material needs'},
    {'value': 'OTHER', 'label': 'Other support'},
    {'value': 'PREFER_NOT_TO_SAY', 'label': 'Prefer not to say'},
]

QUESTIONS = [
    {
        'key': 'attendance_barriers', 'label': 'Are circumstances making regular attendance difficult?',
        'type': 'single_choice', 'choices': SCALE_CHOICES,
    },
    {
        'key': 'school_connection', 'label': 'How connected and supported does the student feel at school?',
        'type': 'single_choice', 'choices': CONNECTION_CHOICES,
    },
    {
        'key': 'support_access', 'label': 'Does the student know an adult at school they can approach for support?',
        'type': 'single_choice', 'choices': ACCESS_CHOICES,
    },
    {
        'key': 'support_requested', 'label': 'Did the student request follow-up support?',
        'type': 'boolean',
    },
    {
        'key': 'support_topics', 'label': 'Which support areas did the student choose to discuss?',
        'type': 'multiple_choice', 'choices': TOPIC_CHOICES,
    },
]


def validate_responses(responses):
    if not isinstance(responses, dict):
        return {'responses': 'Responses must be an object keyed by the approved question identifiers.'}
    errors = {}
    allowed_keys = {question['key'] for question in QUESTIONS}
    extra = set(responses) - allowed_keys
    missing = allowed_keys - set(responses)
    if extra:
        errors['responses'] = f'Unsupported response keys: {", ".join(sorted(extra))}.'
    if missing:
        errors['responses'] = f'Missing required responses: {", ".join(sorted(missing))}.'
    for question in QUESTIONS:
        key = question['key']
        if key not in responses:
            continue
        value = responses[key]
        if question['type'] == 'boolean' and not isinstance(value, bool):
            errors[key] = 'Choose Yes or No.'
        elif question['type'] == 'single_choice':
            choices = {item['value'] for item in question['choices']}
            if value not in choices:
                errors[key] = 'Choose an approved response.'
        elif question['type'] == 'multiple_choice':
            choices = {item['value'] for item in question['choices']}
            if not isinstance(value, list) or len(value) != len(set(value)) or any(item not in choices for item in value):
                errors[key] = 'Choose a unique list of approved support topics.'
            elif 'PREFER_NOT_TO_SAY' in value and len(value) > 1:
                errors[key] = 'Prefer not to say cannot be combined with another support topic.'
    return errors
