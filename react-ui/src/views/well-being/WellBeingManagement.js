import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import {
    Box, Button, Card, CardContent, Checkbox, CircularProgress, Dialog, DialogActions,
    DialogContent, DialogTitle, FormControl, FormControlLabel, Grid, InputLabel, MenuItem,
    Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography
} from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const today = () => {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
const errorMessage = (error) => error.response?.data?.message || Object.entries(error.response?.data || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ') || 'Unable to load restricted check-ins.';
const priorityColor = { ROUTINE: '#43a047', PROMPT: '#fb8c00', URGENT: '#d81b60' };

const WellBeingManagement = () => {
    const token = useSelector((state) => state.account.token);
    const headers = React.useMemo(() => ({ Authorization: `Token ${token}` }), [token]);
    const [records, setRecords] = React.useState([]);
    const [summary, setSummary] = React.useState({});
    const [options, setOptions] = React.useState({ students: [], questions: [], priorities: [], statuses: [] });
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [notice, setNotice] = React.useState('');
    const [search, setSearch] = React.useState('');
    const [statusFilter, setStatusFilter] = React.useState('');
    const [priorityFilter, setPriorityFilter] = React.useState('');
    const [createOpen, setCreateOpen] = React.useState(false);
    const [detail, setDetail] = React.useState(null);
    const [form, setForm] = React.useState({});
    const [workflow, setWorkflow] = React.useState({});

    const load = React.useCallback(() => {
        setLoading(true); setError('');
        Promise.all([
            axios.get(configData.API_SERVER + 'well-being/', { headers, params: { search, status: statusFilter, priority: priorityFilter } }),
            axios.get(configData.API_SERVER + 'well-being/options/', { headers })
        ]).then(([checkInResponse, optionResponse]) => {
            setRecords(checkInResponse.data.records); setSummary(checkInResponse.data.summary); setOptions(optionResponse.data);
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setLoading(false));
    }, [headers, search, statusFilter, priorityFilter]);

    React.useEffect(load, [load]);

    const beginCreate = () => {
        const responses = {};
        options.questions.forEach((question) => {
            responses[question.key] = question.type === 'boolean' ? false : question.type === 'multiple_choice' ? [] : '';
        });
        setForm({
            student: '', conducted_on: today(), privacy_notice_version: options.privacy_notice_version,
            consent_confirmed: false, responses, support_priority: 'ROUTINE', private_notes: '', recommended_actions: ''
        });
        setError(''); setNotice(''); setCreateOpen(true);
    };

    const create = () => {
        setSaving(true); setError(''); setNotice('');
        axios.post(configData.API_SERVER + 'well-being/', form, { headers })
            .then(() => { setCreateOpen(false); setNotice('Restricted check-in recorded.'); load(); })
            .catch((requestError) => setError(errorMessage(requestError))).finally(() => setSaving(false));
    };

    const openDetail = (record) => {
        setError(''); setNotice('');
        axios.get(configData.API_SERVER + `well-being/${record.id}/`, { headers })
            .then((response) => {
                const value = response.data.record;
                setDetail(value);
                setWorkflow({
                    support_priority: value.support_priority, status: value.status,
                    private_notes: value.private_notes || '', recommended_actions: value.recommended_actions || ''
                });
            }).catch((requestError) => setError(errorMessage(requestError)));
    };

    const update = () => {
        setSaving(true); setError(''); setNotice('');
        axios.patch(configData.API_SERVER + `well-being/${detail.id}/`, workflow, { headers })
            .then((response) => { setDetail(response.data.record); setNotice('Restricted follow-up workflow updated.'); load(); })
            .catch((requestError) => setError(errorMessage(requestError))).finally(() => setSaving(false));
    };

    const answerLabel = (question, value) => {
        if (question.type === 'boolean') return value ? 'Yes' : 'No';
        const labels = Object.fromEntries((question.choices || []).map((item) => [item.value, item.label]));
        if (question.type === 'multiple_choice') return value?.length ? value.map((item) => labels[item] || item).join(', ') : 'None selected';
        return labels[value] || value || '—';
    };

    const cards = [
        ['Open', summary.OPEN || 0, '#1e88e5'], ['Action planned', summary.ACTION_PLANNED || 0, '#8e24aa'],
        ['Urgent follow-up', summary.URGENT || 0, '#d81b60'], ['Closed', summary.CLOSED || 0, '#43a047']
    ];

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard><Typography variant="h2">Restricted well-being check-ins</Typography><Typography color="textSecondary">Guidance-only support records. Raw responses and private notes are excluded from automated scoring, Teacher views, guardian views, and list summaries.</Typography></MainCard></Grid>
        {cards.map(([label, value, color]) => <Grid key={label} item lg={3} sm={6} xs={12}><Card sx={{ borderLeft: `5px solid ${color}` }}><CardContent><Typography color="textSecondary">{label}</Typography><Typography variant="h2">{value}</Typography></CardContent></Card></Grid>)}
        <Grid item xs={12}><MainCard title="Check-in register">
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}><TextField size="small" label="Search student or LRN" value={search} onChange={(event) => setSearch(event.target.value)} />
                    <FormControl size="small" sx={{ minWidth: 160 }}><InputLabel>Status</InputLabel><Select value={statusFilter} label="Status" onChange={(event) => setStatusFilter(event.target.value)}><MenuItem value=""><em>All statuses</em></MenuItem>{options.statuses.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl>
                    <FormControl size="small" sx={{ minWidth: 180 }}><InputLabel>Support priority</InputLabel><Select value={priorityFilter} label="Support priority" onChange={(event) => setPriorityFilter(event.target.value)}><MenuItem value=""><em>All priorities</em></MenuItem>{options.priorities.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Box>
                <Button variant="contained" onClick={beginCreate}>New check-in</Button>
            </Box>
            {notice && <Typography sx={{ mb: 2, color: 'success.main' }}>{notice}</Typography>}{error && !createOpen && !detail && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
            {loading ? <Box sx={{ p: 5, textAlign: 'center' }}><CircularProgress /></Box> : <TableContainer><Table>
                <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Student</TableCell><TableCell>Support priority</TableCell><TableCell>Status</TableCell><TableCell>Conducted by</TableCell><TableCell>Reviewed by</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead>
                <TableBody>{records.map((record) => <TableRow key={record.id} hover><TableCell>{record.conducted_on}</TableCell><TableCell>{record.student_name}<br/><Typography variant="caption">{record.learner_reference_number}</Typography></TableCell><TableCell><Typography sx={{ color: priorityColor[record.support_priority], fontWeight: 600 }}>{record.support_priority_label}</Typography></TableCell><TableCell>{record.status_label}</TableCell><TableCell>{record.conducted_by_name}</TableCell><TableCell>{record.reviewed_by_name || '—'}</TableCell><TableCell align="right"><Button size="small" onClick={() => openDetail(record)}>Open restricted record</Button></TableCell></TableRow>)}{!records.length && <TableRow><TableCell colSpan={7} align="center">No restricted check-ins found.</TableCell></TableRow>}</TableBody>
            </Table></TableContainer>}
        </MainCard></Grid>

        <Dialog open={createOpen} onClose={() => setCreateOpen(false)} fullWidth maxWidth="md"><DialogTitle>Record restricted well-being check-in</DialogTitle><DialogContent>
            <Typography color="error" sx={{ mb: 1 }}>Restricted record: enter only information needed for approved student support.</Typography>
            <Typography color="textSecondary" sx={{ mb: 2 }}>Questionnaire {options.questionnaire_version}. This is a support check-in, not a diagnostic instrument.</Typography>
            {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
            <Grid container spacing={2}>
                <Grid item md={8} xs={12}><FormControl fullWidth><InputLabel>Student</InputLabel><Select value={form.student || ''} label="Student" onChange={(event) => setForm({ ...form, student: event.target.value })}>{options.students.map((item) => <MenuItem key={item.id} value={item.id}>{item.name} · {item.lrn}</MenuItem>)}</Select></FormControl></Grid>
                <Grid item md={4} xs={12}><TextField fullWidth type="date" label="Conducted on" value={form.conducted_on || ''} inputProps={{ max: today() }} InputLabelProps={{ shrink: true }} onChange={(event) => setForm({ ...form, conducted_on: event.target.value })} /></Grid>
                {options.questions.map((question) => <Grid key={question.key} item xs={12}>{question.type === 'boolean'
                    ? <FormControlLabel control={<Checkbox checked={Boolean(form.responses?.[question.key])} onChange={(event) => setForm({ ...form, responses: { ...form.responses, [question.key]: event.target.checked } })} />} label={question.label} />
                    : <FormControl fullWidth><InputLabel>{question.label}</InputLabel><Select multiple={question.type === 'multiple_choice'} value={form.responses?.[question.key] ?? (question.type === 'multiple_choice' ? [] : '')} label={question.label} onChange={(event) => setForm({ ...form, responses: { ...form.responses, [question.key]: event.target.value } })}>{(question.choices || []).map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl>}
                </Grid>)}
                <Grid item md={4} xs={12}><FormControl fullWidth><InputLabel>Human-selected support priority</InputLabel><Select value={form.support_priority || 'ROUTINE'} label="Human-selected support priority" onChange={(event) => setForm({ ...form, support_priority: event.target.value })}>{options.priorities.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid>
                <Grid item md={8} xs={12}><TextField fullWidth multiline minRows={2} label="Recommended actions" value={form.recommended_actions || ''} onChange={(event) => setForm({ ...form, recommended_actions: event.target.value })} /></Grid>
                <Grid item xs={12}><TextField fullWidth multiline minRows={2} label="Private guidance notes" value={form.private_notes || ''} onChange={(event) => setForm({ ...form, private_notes: event.target.value })} /></Grid>
                <Grid item xs={12}><FormControlLabel control={<Checkbox checked={Boolean(form.consent_confirmed)} onChange={(event) => setForm({ ...form, consent_confirmed: event.target.checked })} />} label={`Student consent or assent recorded under privacy notice ${options.privacy_notice_version}`} /></Grid>
            </Grid>
        </DialogContent><DialogActions><Button onClick={() => setCreateOpen(false)}>Cancel</Button><Button variant="contained" disabled={saving || !form.student || !form.consent_confirmed} onClick={create}>{saving ? 'Saving…' : 'Record check-in'}</Button></DialogActions></Dialog>

        <Dialog open={Boolean(detail)} onClose={() => setDetail(null)} fullWidth maxWidth="md"><DialogTitle>{detail ? `Restricted check-in — ${detail.student_name}` : 'Restricted check-in'}</DialogTitle><DialogContent>
            {detail && <><Typography color="textSecondary">Conducted {detail.conducted_on} by {detail.conducted_by_name} · {detail.questionnaire_version}</Typography>
                <Typography variant="h3" sx={{ mt: 3, mb: 1 }}>Submitted responses</Typography><TableContainer><Table size="small"><TableBody>{options.questions.map((question) => <TableRow key={question.key}><TableCell sx={{ width: '55%' }}>{question.label}</TableCell><TableCell>{answerLabel(question, detail.responses?.[question.key])}</TableCell></TableRow>)}</TableBody></Table></TableContainer>
                <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>Consent/assent recorded under {detail.privacy_notice_version}. Submitted responses are immutable and do not contribute points to the automated risk score.</Typography>
                <Typography variant="h3" sx={{ mt: 3, mb: 2 }}>Human follow-up</Typography><Grid container spacing={2}><Grid item md={4} xs={12}><FormControl fullWidth disabled={detail.status === 'CLOSED'}><InputLabel>Support priority</InputLabel><Select value={workflow.support_priority || ''} label="Support priority" onChange={(event) => setWorkflow({ ...workflow, support_priority: event.target.value })}>{options.priorities.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid><Grid item md={4} xs={12}><FormControl fullWidth disabled={detail.status === 'CLOSED'}><InputLabel>Status</InputLabel><Select value={workflow.status || ''} label="Status" onChange={(event) => setWorkflow({ ...workflow, status: event.target.value })}>{options.statuses.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid><Grid item xs={12}><TextField fullWidth multiline minRows={2} disabled={detail.status === 'CLOSED'} label="Recommended actions" value={workflow.recommended_actions || ''} onChange={(event) => setWorkflow({ ...workflow, recommended_actions: event.target.value })} /></Grid><Grid item xs={12}><TextField fullWidth multiline minRows={2} disabled={detail.status === 'CLOSED'} label="Private guidance notes" value={workflow.private_notes || ''} onChange={(event) => setWorkflow({ ...workflow, private_notes: event.target.value })} /></Grid></Grid>
                {notice && <Typography sx={{ mt: 2, color: 'success.main' }}>{notice}</Typography>}{error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
            </>}
        </DialogContent><DialogActions><Button onClick={() => setDetail(null)}>Close</Button>{detail?.status !== 'CLOSED' && <Button variant="contained" disabled={saving} onClick={update}>{saving ? 'Saving…' : 'Save follow-up'}</Button>}</DialogActions></Dialog>
    </Grid>;
};

export default WellBeingManagement;
