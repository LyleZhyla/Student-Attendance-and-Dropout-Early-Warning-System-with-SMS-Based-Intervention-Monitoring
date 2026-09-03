import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import {
    Box, Button, Card, CardContent, CircularProgress, FormControl, Grid, InputLabel, MenuItem,
    Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography
} from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const errorMessage = (error) => error.response?.data?.message || Object.entries(error.response?.data || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ') || 'Unable to load SMS notifications.';

const summaryCards = [
    ['QUEUED', 'Queued', '#5e35b1'], ['SENT', 'Sent', '#1e88e5'],
    ['DELIVERED', 'Delivered', '#43a047'], ['FAILED', 'Failed', '#e53935'],
    ['CANCELLED', 'Cancelled', '#757575']
];

const NotificationManagement = () => {
    const token = useSelector((state) => state.account.token);
    const headers = React.useMemo(() => ({ Authorization: `Token ${token}` }), [token]);
    const [records, setRecords] = React.useState([]);
    const [options, setOptions] = React.useState({ recipients: [], categories: [] });
    const [summary, setSummary] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [notice, setNotice] = React.useState('');
    const [status, setStatus] = React.useState('');
    const [search, setSearch] = React.useState('');
    const [form, setForm] = React.useState({ recipient: '', category: 'GENERAL', message: '', event_key: '' });

    const load = React.useCallback(() => {
        setLoading(true); setError('');
        Promise.all([
            axios.get(configData.API_SERVER + 'notifications/', { headers, params: { status, search } }),
            axios.get(configData.API_SERVER + 'notifications/options/', { headers })
        ]).then(([logsResponse, optionsResponse]) => {
            setRecords(logsResponse.data.records);
            setSummary(logsResponse.data.summary);
            setOptions(optionsResponse.data);
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setLoading(false));
    }, [headers, status, search]);

    React.useEffect(load, [load]);

    const queue = () => {
        const recipient = options.recipients.find((item) => String(`${item.student}:${item.guardian}`) === String(form.recipient));
        if (!recipient) { setError('Choose an eligible student and guardian.'); return; }
        setSaving(true); setError(''); setNotice('');
        axios.post(configData.API_SERVER + 'notifications/', {
            student: recipient.student,
            guardian: recipient.guardian,
            category: form.category,
            message: form.message,
            event_key: form.event_key || `manual:${recipient.student}:${recipient.guardian}:${Date.now()}`
        }, { headers }).then(() => {
            setNotice('Notification queued. Review the recipient and use Send when ready.');
            setForm({ recipient: '', category: 'GENERAL', message: '', event_key: '' });
            load();
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setSaving(false));
    };

    const send = (record) => {
        setSaving(true); setError(''); setNotice('');
        axios.post(configData.API_SERVER + `notifications/${record.id}/send/`, {}, { headers })
            .then(() => { setNotice('Provider accepted the notification.'); load(); })
            .catch((requestError) => { setError(errorMessage(requestError)); load(); })
            .finally(() => setSaving(false));
    };

    const eligibleRecipients = options.recipients.filter((item) => item.eligible);

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard>
            <Typography variant="h2">SMS notifications</Typography>
            <Typography color="textSecondary">Queue consent-aware guardian messages, prevent duplicates, and monitor provider attempts.</Typography>
        </MainCard></Grid>

        {summaryCards.map(([key, label, color]) => <Grid key={key} item lg={3} sm={6} xs={12}><Card sx={{ borderLeft: `5px solid ${color}` }}><CardContent>
            <Typography color="textSecondary">{label}</Typography><Typography variant="h2">{summary[key] || 0}</Typography>
        </CardContent></Card></Grid>)}

        <Grid item xs={12}><MainCard title="Queue a guardian notification">
            <Typography color="textSecondary" sx={{ mb: 2 }}>Only linked guardians with recorded consent and a verified mobile number can be selected.</Typography>
            <Grid container spacing={2}>
                <Grid item md={5} xs={12}><FormControl fullWidth><InputLabel>Student and guardian</InputLabel><Select value={form.recipient} label="Student and guardian" onChange={(event) => setForm({ ...form, recipient: event.target.value })}>
                    {eligibleRecipients.map((item) => <MenuItem key={`${item.student}:${item.guardian}`} value={`${item.student}:${item.guardian}`}>{item.student_name} · {item.guardian_name}{item.is_primary ? ' (primary)' : ''}</MenuItem>)}
                </Select></FormControl></Grid>
                <Grid item md={3} xs={12}><FormControl fullWidth><InputLabel>Category</InputLabel><Select value={form.category} label="Category" onChange={(event) => setForm({ ...form, category: event.target.value })}>
                    {options.categories.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
                </Select></FormControl></Grid>
                <Grid item md={4} xs={12}><TextField fullWidth label="Event key (optional)" helperText="Reuse a business event key to block duplicate sends." value={form.event_key} onChange={(event) => setForm({ ...form, event_key: event.target.value })} /></Grid>
                <Grid item xs={12}><TextField fullWidth multiline minRows={3} inputProps={{ maxLength: 480 }} label="Message" value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} helperText={`${form.message.length}/480 characters`} /></Grid>
                <Grid item xs={12}><Button variant="contained" disabled={saving || !form.recipient || !form.message.trim()} onClick={queue}>{saving ? 'Saving…' : 'Queue notification'}</Button></Grid>
            </Grid>
            {!eligibleRecipients.length && <Typography color="textSecondary" sx={{ mt: 2 }}>No eligible recipients. Verify a linked guardian’s mobile number and record SMS consent in Students & Guardians.</Typography>}
            {notice && <Typography sx={{ mt: 2, color: 'success.main' }}>{notice}</Typography>}
            {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
        </MainCard></Grid>

        <Grid item xs={12}><MainCard title="Delivery monitoring">
            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <TextField size="small" label="Search student, guardian, or event key" value={search} onChange={(event) => setSearch(event.target.value)} />
                <FormControl size="small" sx={{ minWidth: 180 }}><InputLabel>Status</InputLabel><Select value={status} label="Status" onChange={(event) => setStatus(event.target.value)}><MenuItem value=""><em>All statuses</em></MenuItem>{summaryCards.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
            </Box>
            {loading ? <Box sx={{ p: 5, textAlign: 'center' }}><CircularProgress /></Box> : <TableContainer><Table size="small">
                <TableHead><TableRow><TableCell>Queued</TableCell><TableCell>Student / guardian</TableCell><TableCell>Category</TableCell><TableCell>Message</TableCell><TableCell>Recipient</TableCell><TableCell>Status</TableCell><TableCell>Attempts</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead>
                <TableBody>{records.map((record) => <TableRow key={record.id} hover>
                    <TableCell>{new Date(record.queued_at).toLocaleString()}</TableCell><TableCell>{record.student_name}<br/><Typography variant="caption">{record.guardian_name}</Typography></TableCell><TableCell>{record.category_label}</TableCell><TableCell sx={{ maxWidth: 300 }}>{record.message}</TableCell><TableCell>{record.recipient_masked}</TableCell><TableCell>{record.status_label}{record.error_message ? <Typography variant="caption" color="error" display="block">{record.error_message}</Typography> : null}</TableCell><TableCell>{record.retry_count}</TableCell><TableCell align="right">{['QUEUED', 'FAILED'].includes(record.status) && <Button size="small" disabled={saving} onClick={() => send(record)}>{record.status === 'FAILED' ? 'Retry' : 'Send'}</Button>}</TableCell>
                </TableRow>)}{!records.length && <TableRow><TableCell colSpan={8} align="center">No notifications found.</TableCell></TableRow>}</TableBody>
            </Table></TableContainer>}
        </MainCard></Grid>
    </Grid>;
};

export default NotificationManagement;
