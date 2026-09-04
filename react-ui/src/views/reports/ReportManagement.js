import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import { Box, Button, CircularProgress, Grid, MenuItem, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@material-ui/core';
import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const localDay = (date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const initialFilters = () => ({ kind: 'attendance', start: localDay(new Date(new Date().getFullYear(), new Date().getMonth(), 1)), end: localDay(new Date()), student: '', action: '', actor: '' });
const message = (error) => error.response?.data?.message || error.response?.data?.detail || Object.entries(error.response?.data || {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ') || 'Unable to load the report.';

const ReportManagement = () => {
    const account = useSelector((state) => state.account);
    const headers = React.useMemo(() => ({ Authorization: `Token ${account.token}` }), [account.token]);
    const authorized = account.user?.is_superuser || ['ADMIN', 'GUIDANCE'].includes(account.user?.role);
    const [filters, setFilters] = React.useState(initialFilters);
    const [applied, setApplied] = React.useState(null);
    const [options, setOptions] = React.useState({ students: [], can_view_audit: false });
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [printing, setPrinting] = React.useState(false);
    const [error, setError] = React.useState('');
    const requestNumber = React.useRef(0);

    React.useEffect(() => {
        if (!authorized) return undefined;
        let active = true;
        axios.get(configData.API_SERVER + 'reports/options/', { headers })
            .then((response) => { if (active) setOptions(response.data); })
            .catch((failure) => { if (active) setError(message(failure)); });
        return () => { active = false; };
    }, [headers, authorized]);

    const parameters = (values, page) => {
        const result = { start: values.start, end: values.end, page };
        if (values.kind === 'audit') {
            if (values.action) result.action = values.action;
            if (values.actor) result.actor = values.actor;
        } else {
            result.kind = values.kind;
            if (values.student) result.student = values.student;
        }
        return result;
    };

    const load = (values, page = 1) => {
        const current = ++requestNumber.current;
        setLoading(true); setError(''); setData(null); setApplied(null);
        axios.get(configData.API_SERVER + (values.kind === 'audit' ? 'audit-logs/' : 'reports/'), { headers, params: parameters(values, page) })
            .then((response) => { if (current === requestNumber.current) { setData(response.data); setApplied({ ...values }); } })
            .catch((failure) => { if (current === requestNumber.current) setError(message(failure)); })
            .finally(() => { if (current === requestNumber.current) setLoading(false); });
    };

    const print = () => {
        const tab = window.open('', '_blank');
        if (!tab) { setError('Allow pop-ups to open the printable report.'); return; }
        tab.opener = null;
        setPrinting(true); setError('');
        axios.post(configData.API_SERVER + 'reports/print/', parameters(applied, 1), { headers, responseType: 'blob' })
            .then((response) => {
                const url = URL.createObjectURL(new Blob([response.data], { type: 'text/html' }));
                tab.location.href = url;
                window.setTimeout(() => URL.revokeObjectURL(url), 60000);
            })
            .catch(async (failure) => {
                tab.close();
                let detail = 'Unable to generate printable report.';
                try { const payload = JSON.parse(await failure.response.data.text()); detail = payload.message || message({ response: { data: payload } }); } catch (_) { /* network failure */ }
                setError(detail);
            }).finally(() => setPrinting(false));
    };

    if (!authorized) return <MainCard><Typography>Reports are restricted to Administrators and Guidance Personnel.</Typography></MainCard>;
    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard><Typography variant="h2">Reports and audit logs</Typography><Typography color="textSecondary">School-use operational reports. Sensitive response content, private notes and intervention findings are excluded.</Typography></MainCard></Grid>
        <Grid item xs={12}><MainCard title="Report filters"><Grid container spacing={2}>
            <Grid item md={3} xs={12}><TextField select fullWidth label="Report" value={filters.kind} onChange={(event) => setFilters({ ...filters, kind: event.target.value })}><MenuItem value="attendance">Attendance records</MenuItem><MenuItem value="interventions">Intervention register</MenuItem><MenuItem value="risk">Confirmed risk assessments</MenuItem>{options.can_view_audit && <MenuItem value="audit">Audit log (Admin only)</MenuItem>}</TextField></Grid>
            {['start', 'end'].map((key) => <Grid item md={2} xs={6} key={key}><TextField fullWidth type="date" label={key === 'start' ? 'From' : 'Through'} value={filters[key]} InputLabelProps={{ shrink: true }} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} /></Grid>)}
            {filters.kind !== 'audit' ? <Grid item md={5} xs={12}><TextField select fullWidth label="Student" value={filters.student} onChange={(event) => setFilters({ ...filters, student: event.target.value })}><MenuItem value="">All students</MenuItem>{options.students.map((student) => <MenuItem key={student.id} value={student.id}>{student.name} · {student.lrn}</MenuItem>)}</TextField></Grid> : <>
                <Grid item md={3} xs={12}><TextField fullWidth label="Exact audit action (optional)" value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value })} helperText="Example: REPORT_GENERATED" /></Grid>
                <Grid item md={2} xs={12}><TextField fullWidth label="Actor ID (optional)" type="number" value={filters.actor} onChange={(event) => setFilters({ ...filters, actor: event.target.value })} /></Grid>
            </>}
            <Grid item xs={12}><Button variant="contained" disabled={loading || !filters.start || !filters.end} onClick={() => load(filters)}>Load preview</Button></Grid>
        </Grid><Typography variant="caption" sx={{ display: 'block', mt: 2 }}>Dates refer to attendance date, intervention creation date, risk assessment date, or audit event date. Intervention status is current. Risk reports show confirmed results only.</Typography></MainCard></Grid>
        <Grid item xs={12}><MainCard title="Preview">
            {error && <Typography role="alert" color="error" sx={{ mb: 2 }}>{error}</Typography>}
            {loading && <CircularProgress />}
            {data && <><Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2, gap: 2 }}><Typography>{applied.kind} · {applied.start} to {applied.end} · {data.total} matching records</Typography>{applied.kind !== 'audit' && <Button variant="outlined" onClick={print} disabled={printing}>{printing ? 'Generating…' : 'Open printable report'}</Button>}</Box>
                <TableContainer><Table size="small"><TableHead><TableRow>{data.columns.map((column) => <TableCell key={column}>{column}</TableCell>)}</TableRow></TableHead><TableBody>{data.rows.map((row, index) => <TableRow key={index}>{row.map((cell, i) => <TableCell key={i}>{cell}</TableCell>)}</TableRow>)}{!data.rows.length && <TableRow><TableCell colSpan={data.columns.length}>No matching records.</TableCell></TableRow>}</TableBody></Table></TableContainer>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mt: 2 }}><Button disabled={data.page <= 1} onClick={() => load(applied, data.page - 1)}>Previous</Button><Typography>Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))}</Typography><Button disabled={data.page * data.page_size >= data.total} onClick={() => load(applied, data.page + 1)}>Next</Button></Box>
                <Typography variant="caption">Preview: 50 rows per page. Printable reports include all matching rows, up to 5,000. Use Ctrl+P in the new tab to print or save as PDF. Audit events are read-only; arbitrary event metadata is not displayed.</Typography>
            </>}
            {!loading && !data && !error && <Typography color="textSecondary">Choose filters and load a preview.</Typography>}
        </MainCard></Grid>
    </Grid>;
};

export default ReportManagement;
