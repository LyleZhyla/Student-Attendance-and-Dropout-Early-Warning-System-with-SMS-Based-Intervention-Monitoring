import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import {
    Box, Button, Card, CardContent, CircularProgress, Dialog, DialogActions, DialogContent,
    DialogTitle, FormControl, Grid, InputLabel, MenuItem, Select, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, TextField, Typography
} from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const emptyCase = { student: '', assigned_to: '', reason: '', status: 'FOR_REVIEW', scheduled_for: '', follow_up_on: '', findings: '' };
const emptyActivity = { activity_type: 'NOTE', guardian: '', channel: '', outcome: '', notes: '', next_action_on: '' };
const errorMessage = (error) => error.response?.data?.message || Object.entries(error.response?.data || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ') || 'Unable to load intervention cases.';
const localDateTime = (value) => value ? new Date(new Date(value).getTime() - new Date(value).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : '';

const InterventionManagement = () => {
    const account = useSelector((state) => state.account);
    const headers = React.useMemo(() => ({ Authorization: `Token ${account.token}` }), [account.token]);
    const [records, setRecords] = React.useState([]);
    const [options, setOptions] = React.useState({ students: [], personnel: [], statuses: [], activity_types: [], channels: [], outcomes: [] });
    const [summary, setSummary] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [notice, setNotice] = React.useState('');
    const [search, setSearch] = React.useState('');
    const [statusFilter, setStatusFilter] = React.useState('');
    const [open, setOpen] = React.useState(false);
    const [selected, setSelected] = React.useState(null);
    const [form, setForm] = React.useState(emptyCase);
    const [activities, setActivities] = React.useState([]);
    const [activity, setActivity] = React.useState(emptyActivity);

    const load = React.useCallback(() => {
        setLoading(true); setError('');
        Promise.all([
            axios.get(configData.API_SERVER + 'interventions/', { headers, params: { search, status: statusFilter } }),
            axios.get(configData.API_SERVER + 'interventions/options/', { headers })
        ]).then(([caseResponse, optionResponse]) => {
            setRecords(caseResponse.data.records); setSummary(caseResponse.data.summary); setOptions(optionResponse.data);
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setLoading(false));
    }, [headers, search, statusFilter]);

    React.useEffect(load, [load]);

    const beginCreate = () => {
        const defaultOwner = options.personnel.length === 1 ? options.personnel[0].id : '';
        setSelected(null); setActivities([]); setActivity(emptyActivity);
        setForm({ ...emptyCase, assigned_to: defaultOwner }); setError(''); setNotice(''); setOpen(true);
    };

    const beginEdit = (record) => {
        setSelected(record); setActivity(emptyActivity); setActivities([]); setError(''); setNotice('');
        setForm({
            student: record.student, assigned_to: record.assigned_to, reason: record.reason, status: record.status,
            scheduled_for: localDateTime(record.scheduled_for), follow_up_on: record.follow_up_on || '', findings: record.findings || ''
        });
        setOpen(true);
        axios.get(configData.API_SERVER + `interventions/${record.id}/activities/`, { headers })
            .then((response) => setActivities(response.data.records)).catch((requestError) => setError(errorMessage(requestError)));
    };

    const saveCase = () => {
        setSaving(true); setError(''); setNotice('');
        const payload = {
            ...form,
            scheduled_for: form.scheduled_for ? new Date(form.scheduled_for).toISOString() : null,
            follow_up_on: form.follow_up_on || null
        };
        const request = selected
            ? axios.patch(configData.API_SERVER + `interventions/${selected.id}/`, payload, { headers })
            : axios.post(configData.API_SERVER + 'interventions/', payload, { headers });
        request.then((response) => {
            setNotice(selected ? 'Case updated.' : 'Intervention case created.');
            if (selected) { setSelected(response.data.record); setForm({ ...form, status: response.data.record.status }); }
            else setOpen(false);
            load();
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setSaving(false));
    };

    const addActivity = () => {
        setSaving(true); setError(''); setNotice('');
        axios.post(configData.API_SERVER + `interventions/${selected.id}/activities/`, {
            ...activity, guardian: activity.guardian || null, channel: activity.channel || '', outcome: activity.outcome || '',
            next_action_on: activity.next_action_on || null
        }, { headers }).then(() => {
            setNotice('Case activity recorded.'); setActivity(emptyActivity);
            return axios.get(configData.API_SERVER + `interventions/${selected.id}/activities/`, { headers });
        }).then((response) => { if (response) setActivities(response.data.records); load(); })
            .catch((requestError) => setError(errorMessage(requestError))).finally(() => setSaving(false));
    };

    const isOwner = account.user?.is_superuser || ['ADMIN', 'GUIDANCE'].includes(account.user?.role) || selected?.assigned_to === account.user?.id;
    const scheduledStatus = ['MEETING_SCHEDULED', 'HOME_VISIT_SCHEDULED'].includes(form.status);
    const openCount = (summary.total || 0) - (summary.RESOLVED || 0) - (summary.CLOSED || 0);
    const cards = [
        ['Open cases', openCount, '#00897b'],
        ['Scheduled', (summary.MEETING_SCHEDULED || 0) + (summary.HOME_VISIT_SCHEDULED || 0), '#1e88e5'],
        ['For follow-up', summary.FOR_FOLLOW_UP || 0, '#fb8c00'],
        ['Resolved / closed', (summary.RESOLVED || 0) + (summary.CLOSED || 0), '#43a047']
    ];

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard><Typography variant="h2">Interventions and home visits</Typography><Typography color="textSecondary">Assign support cases, record parent contact, coordinate meetings or visits, and retain follow-up history.</Typography></MainCard></Grid>
        {cards.map(([label, value, color]) => <Grid key={label} item lg={3} sm={6} xs={12}><Card sx={{ borderLeft: `5px solid ${color}` }}><CardContent><Typography color="textSecondary">{label}</Typography><Typography variant="h2">{value}</Typography></CardContent></Card></Grid>)}
        <Grid item xs={12}><MainCard title="Case register">
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}><TextField size="small" label="Search student, LRN, or reason" value={search} onChange={(event) => setSearch(event.target.value)} />
                    <FormControl size="small" sx={{ minWidth: 190 }}><InputLabel>Status</InputLabel><Select value={statusFilter} label="Status" onChange={(event) => setStatusFilter(event.target.value)}><MenuItem value=""><em>All statuses</em></MenuItem>{options.statuses.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Box>
                <Button variant="contained" onClick={beginCreate}>New case</Button>
            </Box>
            {error && !open && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
            {loading ? <Box sx={{ p: 5, textAlign: 'center' }}><CircularProgress /></Box> : <TableContainer><Table>
                <TableHead><TableRow><TableCell>Student</TableCell><TableCell>Reason</TableCell><TableCell>Status</TableCell><TableCell>Owner</TableCell><TableCell>Schedule / follow-up</TableCell><TableCell>Last activity</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead>
                <TableBody>{records.map((record) => <TableRow key={record.id} hover><TableCell>{record.student_name}<br/><Typography variant="caption">{record.learner_reference_number}</Typography></TableCell><TableCell sx={{ maxWidth: 320 }}>{record.reason}</TableCell><TableCell>{record.status_label}</TableCell><TableCell>{record.assigned_to_name}</TableCell><TableCell>{record.scheduled_for ? new Date(record.scheduled_for).toLocaleString() : record.follow_up_on || '—'}</TableCell><TableCell>{record.last_activity_at ? new Date(record.last_activity_at).toLocaleString() : '—'}<br/><Typography variant="caption">{record.activity_count} entries</Typography></TableCell><TableCell align="right"><Button size="small" onClick={() => beginEdit(record)}>Open</Button></TableCell></TableRow>)}
                    {!records.length && <TableRow><TableCell colSpan={7} align="center">No intervention cases found.</TableCell></TableRow>}
                </TableBody>
            </Table></TableContainer>}
        </MainCard></Grid>

        <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md"><DialogTitle>{selected ? `Case for ${selected.student_name}` : 'Create intervention case'}</DialogTitle><DialogContent>
            {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}{notice && <Typography sx={{ mb: 2, color: 'success.main' }}>{notice}</Typography>}
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
                <Grid item md={6} xs={12}><FormControl fullWidth disabled={Boolean(selected)}><InputLabel>Student</InputLabel><Select value={form.student} label="Student" onChange={(event) => setForm({ ...form, student: event.target.value })}>{options.students.map((item) => <MenuItem key={item.id} value={item.id}>{item.name} · {item.lrn}</MenuItem>)}</Select></FormControl></Grid>
                <Grid item md={6} xs={12}><FormControl fullWidth disabled={Boolean(selected && !isOwner)}><InputLabel>Case owner</InputLabel><Select value={form.assigned_to} label="Case owner" onChange={(event) => setForm({ ...form, assigned_to: event.target.value })}>{options.personnel.map((item) => <MenuItem key={item.id} value={item.id}>{item.name} · {item.role}</MenuItem>)}</Select></FormControl></Grid>
                <Grid item xs={12}><TextField fullWidth multiline minRows={2} disabled={Boolean(selected && !isOwner)} label="Reason for support" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></Grid>
                {selected && <Grid item md={4} xs={12}><FormControl fullWidth disabled={!isOwner}><InputLabel>Status</InputLabel><Select value={form.status} label="Status" onChange={(event) => setForm({ ...form, status: event.target.value })}>{options.statuses.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid>}
                {selected && scheduledStatus && <Grid item md={4} xs={12}><TextField fullWidth disabled={!isOwner} type="datetime-local" label="Meeting / visit schedule" value={form.scheduled_for} InputLabelProps={{ shrink: true }} onChange={(event) => setForm({ ...form, scheduled_for: event.target.value })} /></Grid>}
                {selected && form.status === 'FOR_FOLLOW_UP' && <Grid item md={4} xs={12}><TextField fullWidth disabled={!isOwner} type="date" label="Follow-up date" value={form.follow_up_on} InputLabelProps={{ shrink: true }} onChange={(event) => setForm({ ...form, follow_up_on: event.target.value })} /></Grid>}
                {selected && <Grid item xs={12}><TextField fullWidth multiline minRows={2} disabled={!isOwner} label="Findings and resolution notes" value={form.findings} onChange={(event) => setForm({ ...form, findings: event.target.value })} /></Grid>}
            </Grid>
            {selected && <Box sx={{ mt: 4 }}><Typography variant="h3" sx={{ mb: 2 }}>Case activity</Typography>
                {isOwner && <Grid container spacing={2}>
                    <Grid item md={4} xs={12}><FormControl fullWidth><InputLabel>Activity</InputLabel><Select value={activity.activity_type} label="Activity" onChange={(event) => setActivity({ ...activity, activity_type: event.target.value })}>{options.activity_types.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid>
                    {activity.activity_type === 'PARENT_CONTACT' && <><Grid item md={4} xs={12}><FormControl fullWidth><InputLabel>Guardian</InputLabel><Select value={activity.guardian} label="Guardian" onChange={(event) => setActivity({ ...activity, guardian: event.target.value })}>{(selected.guardians || []).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}{item.is_primary ? ' (primary)' : ''}</MenuItem>)}</Select></FormControl></Grid><Grid item md={4} xs={12}><FormControl fullWidth><InputLabel>Channel</InputLabel><Select value={activity.channel} label="Channel" onChange={(event) => setActivity({ ...activity, channel: event.target.value })}>{options.channels.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid><Grid item md={4} xs={12}><FormControl fullWidth><InputLabel>Outcome</InputLabel><Select value={activity.outcome} label="Outcome" onChange={(event) => setActivity({ ...activity, outcome: event.target.value })}>{options.outcomes.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid></>}
                    <Grid item md={activity.activity_type === 'PARENT_CONTACT' ? 8 : 12} xs={12}><TextField fullWidth multiline minRows={2} label="Activity notes" value={activity.notes} onChange={(event) => setActivity({ ...activity, notes: event.target.value })} /></Grid>
                    <Grid item xs={12}><Button variant="outlined" disabled={saving || !activity.notes.trim()} onClick={addActivity}>Add activity</Button></Grid>
                </Grid>}
                <TableContainer sx={{ mt: 2 }}><Table size="small"><TableHead><TableRow><TableCell>Date</TableCell><TableCell>Activity</TableCell><TableCell>Guardian / outcome</TableCell><TableCell>Notes</TableCell><TableCell>Recorded by</TableCell></TableRow></TableHead><TableBody>{activities.map((item) => <TableRow key={item.id}><TableCell>{new Date(item.occurred_at).toLocaleString()}</TableCell><TableCell>{item.activity_type_label}{item.channel_label ? ` · ${item.channel_label}` : ''}</TableCell><TableCell>{item.guardian_name || '—'}{item.outcome_label ? ` · ${item.outcome_label}` : ''}</TableCell><TableCell>{item.notes}</TableCell><TableCell>{item.recorded_by_name}</TableCell></TableRow>)}{!activities.length && <TableRow><TableCell colSpan={5} align="center">No case activity recorded.</TableCell></TableRow>}</TableBody></Table></TableContainer>
            </Box>}
        </DialogContent><DialogActions><Button onClick={() => setOpen(false)}>Close</Button>{(!selected || isOwner) && <Button variant="contained" disabled={saving || !form.student || !form.assigned_to || !form.reason.trim()} onClick={saveCase}>{saving ? 'Saving…' : selected ? 'Save case' : 'Create case'}</Button>}</DialogActions></Dialog>
    </Grid>;
};

export default InterventionManagement;
