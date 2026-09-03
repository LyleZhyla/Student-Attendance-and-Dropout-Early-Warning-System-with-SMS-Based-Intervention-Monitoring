import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import {
    Box, Button, Chip, CircularProgress, FormControl, Grid, InputLabel, MenuItem, Select,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography
} from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const statusColors = {
    PRESENT: 'success', LATE: 'warning', ABSENT_EXCUSED: 'default',
    ABSENT_UNEXCUSED: 'error', SCHOOL_ACTIVITY: 'primary', NOT_RECORDED: 'default'
};

const errorMessage = (error) => error.response?.data?.message || Object.entries(error.response?.data || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? JSON.stringify(value) : value}`).join(' ') || 'Unable to connect to TardyTrack.';

const localDate = () => {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};

const AttendanceManagement = () => {
    const account = useSelector((state) => state.account);
    const canEncode = ['ADMIN', 'TEACHER'].includes(account.user?.role) || account.user?.is_superuser;
    const headers = React.useMemo(() => ({ Authorization: `Token ${account.token}` }), [account.token]);
    const [schedules, setSchedules] = React.useState([]);
    const [statuses, setStatuses] = React.useState([]);
    const [schedule, setSchedule] = React.useState('');
    const [date, setDate] = React.useState(localDate());
    const [roster, setRoster] = React.useState([]);
    const [history, setHistory] = React.useState([]);
    const [summary, setSummary] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [notice, setNotice] = React.useState('');

    const loadHistory = React.useCallback(() => {
        axios.get(configData.API_SERVER + 'attendance/records/', { headers }).then((response) => {
            setHistory(response.data.records);
            setSummary(response.data.summary);
        }).catch((requestError) => setError(errorMessage(requestError)));
    }, [headers]);

    React.useEffect(() => {
        setLoading(true);
        const requests = [axios.get(configData.API_SERVER + 'attendance/records/', { headers })];
        if (canEncode) requests.push(axios.get(configData.API_SERVER + 'attendance/options/', { headers }));
        Promise.all(requests).then(([recordsResponse, optionsResponse]) => {
            setHistory(recordsResponse.data.records);
            setSummary(recordsResponse.data.summary);
            if (optionsResponse) {
                setSchedules(optionsResponse.data.schedules);
                setStatuses(optionsResponse.data.statuses);
                if (optionsResponse.data.schedules.length) setSchedule(optionsResponse.data.schedules[0].id);
            }
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setLoading(false));
    }, [canEncode, headers]);

    const loadRoster = () => {
        if (!schedule || !date) return;
        setLoading(true); setError(''); setNotice('');
        axios.get(configData.API_SERVER + 'attendance/roster/', {
            headers, params: { schedule, date }
        }).then((response) => setRoster(response.data.roster))
            .catch((requestError) => { setRoster([]); setError(errorMessage(requestError)); })
            .finally(() => setLoading(false));
    };

    const changeEntry = (student, values) => setRoster((current) => current.map((entry) => (
        entry.student === student ? { ...entry, ...values } : entry
    )));

    const markAllPresent = () => setRoster((current) => current.map((entry) => ({
        ...entry, status: 'PRESENT', excuse_reason: ''
    })));

    const save = () => {
        setSaving(true); setError(''); setNotice('');
        const records = roster.map(({ student, status, time_in, excuse_reason }) => ({
            student, status, time_in: time_in || null,
            excuse_reason: status === 'ABSENT_EXCUSED' ? excuse_reason : ''
        }));
        axios.post(configData.API_SERVER + 'attendance/bulk/', { schedule, date, records }, { headers })
            .then((response) => {
                loadRoster();
                setNotice(response.data.message);
                loadHistory();
            }).catch((requestError) => setError(errorMessage(requestError)))
            .finally(() => setSaving(false));
    };

    if (loading && !history.length && !roster.length) {
        return <Box sx={{ minHeight: 360, display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>;
    }

    const statusLabel = (value) => statuses.find((item) => item.value === value)?.label || value.replaceAll('_', ' ');

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard>
            <Typography variant="h2">Attendance</Typography>
            <Typography color="textSecondary">{canEncode ? 'Load an assigned class roster, encode attendance in one pass, and safely correct saved entries.' : 'Review your authorized attendance history.'}</Typography>
        </MainCard></Grid>

        {canEncode && <Grid item xs={12}><MainCard title="Encode class attendance">
            <Grid container spacing={2} alignItems="flex-end">
                <Grid item md={6} xs={12}><FormControl fullWidth><InputLabel>Class schedule</InputLabel><Select value={schedule} label="Class schedule" onChange={(event) => { setSchedule(event.target.value); setRoster([]); }}>
                    {schedules.map((item) => <MenuItem key={item.id} value={item.id}>{item.name} · {item.weekday_label} {String(item.starts_at).slice(0, 5)} · {item.school_year}</MenuItem>)}
                </Select></FormControl></Grid>
                <Grid item md={3} xs={12}><TextField fullWidth label="Attendance date" type="date" value={date} inputProps={{ max: localDate() }} InputLabelProps={{ shrink: true }} onChange={(event) => { setDate(event.target.value); setRoster([]); }} /></Grid>
                <Grid item md={3} xs={12}><Button fullWidth variant="contained" disabled={!schedule || !date || loading} onClick={loadRoster}>{loading ? 'Loading…' : 'Load roster'}</Button></Grid>
            </Grid>
            {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
            {notice && <Typography color="primary" sx={{ mt: 2 }}>{notice}</Typography>}
            {roster.length > 0 && <>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', my: 2, gap: 2 }}>
                    <Typography>{roster.length} actively enrolled student{roster.length === 1 ? '' : 's'}</Typography>
                    <Button variant="outlined" onClick={markAllPresent}>Mark all present</Button>
                </Box>
                <TableContainer><Table size="small">
                    <TableHead><TableRow><TableCell>LRN</TableCell><TableCell>Student</TableCell><TableCell>Status</TableCell><TableCell>Time in</TableCell><TableCell>Excuse reason</TableCell></TableRow></TableHead>
                    <TableBody>{roster.map((entry) => <TableRow key={entry.student}>
                        <TableCell>{entry.learner_reference_number}</TableCell><TableCell>{entry.student_name}</TableCell>
                        <TableCell sx={{ minWidth: 190 }}><FormControl fullWidth size="small"><Select value={entry.status} onChange={(event) => changeEntry(entry.student, { status: event.target.value, excuse_reason: event.target.value === 'ABSENT_EXCUSED' ? entry.excuse_reason : '' })}>
                            {statuses.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
                        </Select></FormControl></TableCell>
                        <TableCell><TextField type="time" value={entry.time_in ? String(entry.time_in).slice(0, 5) : ''} onChange={(event) => changeEntry(entry.student, { time_in: event.target.value })} inputProps={{ 'aria-label': `Time in for ${entry.student_name}` }} /></TableCell>
                        <TableCell><TextField fullWidth disabled={entry.status !== 'ABSENT_EXCUSED'} required={entry.status === 'ABSENT_EXCUSED'} placeholder={entry.status === 'ABSENT_EXCUSED' ? 'Required' : 'Not applicable'} value={entry.excuse_reason || ''} onChange={(event) => changeEntry(entry.student, { excuse_reason: event.target.value })} /></TableCell>
                    </TableRow>)}</TableBody>
                </Table></TableContainer>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}><Button variant="contained" disabled={saving} onClick={save}>{saving ? 'Saving…' : 'Save attendance'}</Button></Box>
            </>}
            {!loading && schedule && !roster.length && <Typography sx={{ mt: 3 }} color="textSecondary">Choose a valid scheduled class date, then load the roster.</Typography>}
            {!schedules.length && <Typography sx={{ mt: 2 }} color="textSecondary">No class schedules are assigned to this account.</Typography>}
        </MainCard></Grid>}

        <Grid item xs={12}><MainCard title="Attendance history">
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                <Chip label={`Total ${summary.total || 0}`} />
                <Chip color="primary" label={`Present ${summary.PRESENT || 0}`} />
                <Chip label={`Late ${summary.LATE || 0}`} />
                <Chip label={`Absent ${(summary.ABSENT_EXCUSED || 0) + (summary.ABSENT_UNEXCUSED || 0)}`} />
            </Box>
            {!canEncode && error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
            <TableContainer><Table size="small">
                <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Student</TableCell><TableCell>Class</TableCell><TableCell>Status</TableCell><TableCell>Time in</TableCell><TableCell>Reason</TableCell></TableRow></TableHead>
                <TableBody>{history.map((record) => <TableRow key={record.id} hover>
                    <TableCell>{record.date}</TableCell><TableCell>{record.student_name}</TableCell><TableCell>{record.schedule_name}</TableCell>
                    <TableCell><Chip size="small" color={statusColors[record.status]} label={record.status_label || statusLabel(record.status)} /></TableCell>
                    <TableCell>{record.time_in ? String(record.time_in).slice(0, 5) : '—'}</TableCell><TableCell>{record.excuse_reason || '—'}</TableCell>
                </TableRow>)}{!history.length && <TableRow><TableCell colSpan={6} align="center">No attendance records yet.</TableCell></TableRow>}</TableBody>
            </Table></TableContainer>
        </MainCard></Grid>
    </Grid>;
};

export default AttendanceManagement;
