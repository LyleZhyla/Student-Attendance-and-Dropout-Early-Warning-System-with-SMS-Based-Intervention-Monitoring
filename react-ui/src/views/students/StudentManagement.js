import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import {
    Box, Button, Checkbox, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
    FormControl, Grid, InputLabel, MenuItem, Select, Tab, Tabs, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, TextField, Typography
} from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const definitions = {
    students: {
        title: 'Students', columns: [['learner_reference_number', 'LRN'], ['full_name', 'Student'], ['current_section', 'Current section'], ['guardian_names', 'Guardians'], ['is_active', 'Active']],
        empty: { learner_reference_number: '', first_name: '', middle_name: '', last_name: '', birth_date: '', address: '', user: '', is_active: true },
        fields: [['learner_reference_number', 'Learner reference number', 'text'], ['first_name', 'First name', 'text'], ['middle_name', 'Middle name', 'text'], ['last_name', 'Last name', 'text'], ['birth_date', 'Birth date', 'date'], ['address', 'Address', 'text'], ['user', 'Student login (optional)', 'student_accounts'], ['is_active', 'Active student', 'boolean']]
    },
    guardians: {
        title: 'Guardians', columns: [['full_name', 'Guardian'], ['relationship', 'Relationship'], ['mobile_number', 'Mobile'], ['student_count', 'Students'], ['mobile_verified', 'Mobile verified'], ['sms_consent', 'SMS consent']],
        empty: { full_name: '', relationship: '', mobile_number: '', email: '', address: '', sms_consent: false, mobile_verified: false, user: '' },
        fields: [['full_name', 'Full name', 'text'], ['relationship', 'Relationship', 'text'], ['mobile_number', 'Mobile number', 'text'], ['email', 'Email', 'email'], ['address', 'Address', 'text'], ['user', 'Parent login (optional)', 'parent_accounts'], ['mobile_verified', 'Mobile number verified', 'boolean'], ['sms_consent', 'SMS consent recorded', 'boolean']]
    },
    enrollments: {
        title: 'Enrollments', columns: [['student_name', 'Student'], ['section_name', 'Section'], ['school_year_name', 'School year'], ['status', 'Status'], ['enrolled_on', 'Enrolled on']],
        empty: { student: '', section: '', status: 'ENROLLED', enrolled_on: new Date().toISOString().slice(0, 10) },
        fields: [['student', 'Student', 'students'], ['section', 'Section', 'sections'], ['status', 'Status', 'statuses'], ['enrolled_on', 'Enrollment date', 'date']]
    },
    'student-guardians': {
        title: 'Guardian links', columns: [['student_name', 'Student'], ['guardian_name', 'Guardian'], ['is_primary', 'Primary']],
        empty: { student: '', guardian: '', is_primary: false },
        fields: [['student', 'Student', 'students'], ['guardian', 'Guardian', 'guardians'], ['is_primary', 'Primary guardian', 'boolean']]
    }
};

const message = (error) => error.response?.data?.message || Object.entries(error.response?.data || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ') || 'Unable to connect to TardyTrack.';

const StudentManagement = () => {
    const token = useSelector((state) => state.account.token);
    const headers = React.useMemo(() => ({ Authorization: `Token ${token}` }), [token]);
    const [tab, setTab] = React.useState('students');
    const [records, setRecords] = React.useState([]);
    const [options, setOptions] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [search, setSearch] = React.useState('');
    const [editing, setEditing] = React.useState(null);
    const [form, setForm] = React.useState(definitions.students.empty);
    const [open, setOpen] = React.useState(false);
    const definition = definitions[tab];
    const visibleRecords = records.filter((record) => JSON.stringify(record).toLowerCase().includes(search.toLowerCase()));

    const load = React.useCallback(() => {
        setLoading(true); setError('');
        const endpoint = tab === 'student-guardians' ? 'student-guardians/' : `${tab}/`;
        Promise.all([
            axios.get(configData.API_SERVER + endpoint, { headers }),
            axios.get(configData.API_SERVER + 'students/options/', { headers }),
            axios.get(configData.API_SERVER + 'students/', { headers }),
            axios.get(configData.API_SERVER + 'guardians/', { headers })
        ]).then(([recordsResponse, optionsResponse, studentsResponse, guardiansResponse]) => {
            setRecords(recordsResponse.data.records);
            setOptions({ ...optionsResponse.data, students: studentsResponse.data.records.map((x) => ({ id: x.id, name: x.full_name })), guardians: guardiansResponse.data.records.map((x) => ({ id: x.id, name: x.full_name })) });
        }).catch((requestError) => setError(message(requestError))).finally(() => setLoading(false));
    }, [headers, tab]);

    React.useEffect(load, [load]);

    const begin = (record = null) => {
        setEditing(record);
        setForm(record ? definition.fields.reduce((values, [name]) => ({ ...values, [name]: record[name] ?? '' }), {}) : { ...definition.empty });
        setError(''); setOpen(true);
    };

    const save = () => {
        const endpoint = tab === 'student-guardians' ? 'student-guardians' : tab;
        const url = configData.API_SERVER + `${endpoint}/${editing ? `${editing.id}/` : ''}`;
        const payload = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value === '' && ['user', 'birth_date'].includes(key) ? null : value]));
        const request = editing ? axios.patch(url, payload, { headers }) : axios.post(url, payload, { headers });
        request.then(() => { setOpen(false); load(); }).catch((requestError) => setError(message(requestError)));
    };

    const display = (record, key) => {
        if (key === 'guardian_names') return record.guardians?.map((guardian) => `${guardian.full_name}${guardian.is_primary ? ' (primary)' : ''}`).join(', ') || '—';
        if (['is_active', 'sms_consent', 'mobile_verified', 'is_primary'].includes(key)) return record[key] ? 'Yes' : 'No';
        return record[key] ?? '—';
    };

    const renderField = ([name, label, type]) => {
        if (type === 'boolean') return <Box key={name}><Checkbox checked={Boolean(form[name])} onChange={(event) => setForm({ ...form, [name]: event.target.checked })} />{label}</Box>;
        const choices = options[type];
        if (choices) return <FormControl key={name} fullWidth><InputLabel>{label}</InputLabel><Select value={form[name] ?? ''} label={label} onChange={(event) => setForm({ ...form, [name]: event.target.value })}>
            {['student_accounts', 'parent_accounts'].includes(type) && <MenuItem value=""><em>No linked login</em></MenuItem>}
            {choices.map((choice) => <MenuItem key={choice.id ?? choice.value} value={choice.id ?? choice.value}>{choice.name ?? choice.label}{choice.school_year ? ` · ${choice.school_year}` : ''}</MenuItem>)}
        </Select></FormControl>;
        return <TextField key={name} fullWidth required={!['middle_name', 'birth_date', 'address', 'email'].includes(name)} label={label} type={type} value={form[name] ?? ''} InputLabelProps={type === 'date' ? { shrink: true } : undefined} onChange={(event) => setForm({ ...form, [name]: event.target.value })} />;
    };

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard><Typography variant="h2">Students and guardians</Typography><Typography color="textSecondary">Maintain student profiles, guardian consent and links, and school-year enrollments.</Typography></MainCard></Grid>
        <Grid item xs={12}><MainCard>
            <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable">{Object.entries(definitions).map(([key, value]) => <Tab key={key} value={key} label={value.title} />)}</Tabs>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, my: 2 }}><TextField size="small" label="Search" value={search} onChange={(event) => setSearch(event.target.value)} /><Button variant="contained" onClick={() => begin()}>Add record</Button></Box>
            {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
            {loading ? <Box sx={{ p: 5, textAlign: 'center' }}><CircularProgress /></Box> : <TableContainer><Table>
                <TableHead><TableRow>{definition.columns.map(([key, label]) => <TableCell key={key}>{label}</TableCell>)}<TableCell align="right">Action</TableCell></TableRow></TableHead>
                <TableBody>{visibleRecords.map((record) => <TableRow key={record.id} hover>{definition.columns.map(([key]) => <TableCell key={key}>{display(record, key)}</TableCell>)}<TableCell align="right"><Button size="small" onClick={() => begin(record)}>Edit</Button></TableCell></TableRow>)}
                    {!visibleRecords.length && <TableRow><TableCell colSpan={definition.columns.length + 1} align="center">No matching records.</TableCell></TableRow>}
                </TableBody>
            </Table></TableContainer>}
        </MainCard></Grid>
        <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm"><DialogTitle>{editing ? 'Edit' : 'Add'} {definition.title.toLowerCase()}</DialogTitle><DialogContent>
            {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
            <Grid container spacing={2} sx={{ mt: 0.5 }}>{definition.fields.map((field) => <Grid key={field[0]} item xs={12} sm={field[2] === 'boolean' ? 12 : 6}>{renderField(field)}</Grid>)}</Grid>
        </DialogContent><DialogActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button variant="contained" onClick={save}>Save</Button></DialogActions></Dialog>
    </Grid>;
};

export default StudentManagement;
