import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import Chart from 'react-apexcharts';
import {
    Box, Button, Card, CardContent, CircularProgress, FormControl, Grid, InputLabel, MenuItem,
    Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography
} from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const currentMonth = () => {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 7);
};

const errorMessage = (error) => error.response?.data?.message || 'Attendance analytics are unavailable.';
const metricCards = [
    ['attendance_rate', 'Attendance rate', '%', '#43a047'],
    ['punctuality_rate', 'Punctuality', '%', '#1e88e5'],
    ['absences', 'Absences', '', '#e53935'],
    ['late', 'Late records', '', '#fb8c00']
];

const AttendanceAnalytics = () => {
    const token = useSelector((state) => state.account.token);
    const headers = React.useMemo(() => ({ Authorization: `Token ${token}` }), [token]);
    const [month, setMonth] = React.useState(currentMonth());
    const [schedule, setSchedule] = React.useState('');
    const [student, setStudent] = React.useState('');
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');

    const load = React.useCallback((params = {}) => {
        setLoading(true); setError('');
        axios.get(configData.API_SERVER + 'attendance/analytics/', {
            headers,
            params: { month: params.month ?? month, schedule: params.schedule ?? schedule, student: params.student ?? student }
        }).then((response) => setData(response.data))
            .catch((requestError) => setError(errorMessage(requestError)))
            .finally(() => setLoading(false));
    }, [headers, month, schedule, student]);

    React.useEffect(() => {
        setLoading(true); setError('');
        axios.get(configData.API_SERVER + 'attendance/analytics/', { headers, params: { month: currentMonth() } })
            .then((response) => setData(response.data))
            .catch((requestError) => setError(errorMessage(requestError)))
            .finally(() => setLoading(false));
    }, [headers]);

    const summary = data?.summary || {};
    const schedules = data?.filter_options?.schedules || [];
    const students = data?.filter_options?.students || [];
    const daily = data?.daily_trend || [];
    const monthly = data?.monthly_trend || [];
    const distributionOptions = {
        labels: ['Present', 'Late', 'Excused absence', 'Unexcused absence', 'School activity', 'Not recorded'],
        colors: ['#43a047', '#fb8c00', '#7e57c2', '#e53935', '#1e88e5', '#9e9e9e'],
        legend: { position: 'bottom' }, dataLabels: { enabled: true }, noData: { text: 'No records' }
    };
    const dailyOptions = {
        chart: { stacked: true, toolbar: { show: false } },
        xaxis: { categories: daily.map((item) => item.date), labels: { rotate: -45 } },
        colors: ['#43a047', '#fb8c00', '#e53935', '#1e88e5'],
        legend: { position: 'top' }, dataLabels: { enabled: false },
        yaxis: { title: { text: 'Attendance records' }, min: 0, forceNiceScale: true }
    };
    const monthlyOptions = {
        chart: { toolbar: { show: false } }, stroke: { curve: 'smooth', width: 3 },
        xaxis: { categories: monthly.map((item) => item.label) }, colors: ['#5e35b1'],
        yaxis: { min: 0, max: 100, title: { text: 'Attendance rate (%)' } },
        dataLabels: { enabled: false }, tooltip: { y: { formatter: (value) => `${value}%` } }
    };

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard>
            <Typography variant="h2">Attendance analytics</Typography>
            <Typography color="textSecondary">Monthly summaries and attendance-event monitoring within your authorized students and classes.</Typography>
        </MainCard></Grid>

        <Grid item xs={12}><MainCard title="Filters">
            <Grid container spacing={2} alignItems="flex-end">
                <Grid item md={3} xs={12}><TextField fullWidth type="month" label="Month" value={month} inputProps={{ max: currentMonth() }} InputLabelProps={{ shrink: true }} onChange={(event) => setMonth(event.target.value)} /></Grid>
                <Grid item md={4} xs={12}><FormControl fullWidth><InputLabel>Class schedule</InputLabel><Select value={schedule} label="Class schedule" onChange={(event) => setSchedule(event.target.value)}>
                    <MenuItem value=""><em>All authorized schedules</em></MenuItem>
                    {schedules.map((item) => <MenuItem key={item.id} value={item.id}>{item.name} · {item.weekday_label}</MenuItem>)}
                </Select></FormControl></Grid>
                <Grid item md={3} xs={12}><FormControl fullWidth><InputLabel>Student</InputLabel><Select value={student} label="Student" onChange={(event) => setStudent(event.target.value)}>
                    <MenuItem value=""><em>All authorized students</em></MenuItem>
                    {students.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
                </Select></FormControl></Grid>
                <Grid item md={2} xs={12}><Button fullWidth variant="contained" disabled={loading || !month} onClick={() => load()}>{loading ? 'Loading…' : 'Apply'}</Button></Grid>
            </Grid>
            {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
        </MainCard></Grid>

        {loading && !data ? <Grid item xs={12}><Box sx={{ p: 8, textAlign: 'center' }}><CircularProgress /></Box></Grid> : <>
            {metricCards.map(([key, label, suffix, color]) => <Grid item lg={3} sm={6} xs={12} key={key}><Card sx={{ height: '100%', borderLeft: `5px solid ${color}` }}><CardContent>
                <Typography color="textSecondary">{label}</Typography><Typography variant="h2" sx={{ mt: 1 }}>{key === 'late' ? summary.LATE || 0 : summary[key] || 0}{suffix}</Typography>
                <Typography variant="caption">{data?.period?.label || month}</Typography>
            </CardContent></Card></Grid>)}

            <Grid item md={7} xs={12}><MainCard title="Daily attendance distribution">
                <Chart type="bar" height={330} options={dailyOptions} series={[
                    { name: 'Present', data: daily.map((item) => item.PRESENT) },
                    { name: 'Late', data: daily.map((item) => item.LATE) },
                    { name: 'Absent', data: daily.map((item) => item.absences) },
                    { name: 'School activity', data: daily.map((item) => item.SCHOOL_ACTIVITY) }
                ]} />
            </MainCard></Grid>
            <Grid item md={5} xs={12}><MainCard title="Status distribution">
                <Chart type="donut" height={330} options={distributionOptions} series={[
                    summary.PRESENT || 0, summary.LATE || 0, summary.ABSENT_EXCUSED || 0,
                    summary.ABSENT_UNEXCUSED || 0, summary.SCHOOL_ACTIVITY || 0, summary.NOT_RECORDED || 0
                ]} />
            </MainCard></Grid>
            <Grid item xs={12}><MainCard title="Six-month attendance trend">
                <Chart type="line" height={300} options={monthlyOptions} series={[{ name: 'Attendance rate', data: monthly.map((item) => item.attendance_rate) }]} />
            </MainCard></Grid>

            <Grid item xs={12}><MainCard title="Student attendance monitoring">
                <Typography color="textSecondary" sx={{ mb: 2 }}>{data?.methodology?.monitoring}</Typography>
                <TableContainer><Table size="small">
                    <TableHead><TableRow><TableCell>LRN</TableCell><TableCell>Student</TableCell><TableCell align="right">Rate</TableCell><TableCell align="right">Present</TableCell><TableCell align="right">Late</TableCell><TableCell align="right">Excused</TableCell><TableCell align="right">Unexcused</TableCell><TableCell align="right">Events to review</TableCell></TableRow></TableHead>
                    <TableBody>{(data?.student_breakdown || []).map((item) => <TableRow key={item.student} hover>
                        <TableCell>{item.learner_reference_number}</TableCell><TableCell>{item.student_name}</TableCell><TableCell align="right">{item.attendance_rate}%</TableCell>
                        <TableCell align="right">{item.PRESENT}</TableCell><TableCell align="right">{item.LATE}</TableCell><TableCell align="right">{item.ABSENT_EXCUSED}</TableCell><TableCell align="right">{item.ABSENT_UNEXCUSED}</TableCell><TableCell align="right">{item.monitoring_events}</TableCell>
                    </TableRow>)}{!data?.student_breakdown?.length && <TableRow><TableCell colSpan={8} align="center">No attendance records for this period.</TableCell></TableRow>}</TableBody>
                </Table></TableContainer>
                <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 2 }}>{data?.methodology?.attendance_rate}</Typography>
            </MainCard></Grid>
        </>}
    </Grid>;
};

export default AttendanceAnalytics;
