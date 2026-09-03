import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import Chart from 'react-apexcharts';
import { Box, Card, CardContent, Chip, CircularProgress, Grid, LinearProgress, Typography } from '@material-ui/core';

import configData from '../../../config';
import MainCard from '../../../ui-component/cards/MainCard';
import { gridSpacing } from '../../../store/constant';

const fallbackMetricCards = [
    { key: 'active_students', label: 'Active Students', note: 'Enrolled student profiles', color: '#5e35b1' },
    { key: 'attendance_recorded_today', label: 'Recorded Today', note: 'Attendance entries today', color: '#1e88e5' },
    { key: 'late_today', label: 'Late Today', note: 'Needs attendance review', color: '#fb8c00' },
    { key: 'absent_today', label: 'Absent Today', note: 'Excused and unexcused', color: '#e53935' },
    { key: 'high_risk_records', label: 'High-Risk Records', note: 'Requires human validation', color: '#d81b60' },
    { key: 'open_interventions', label: 'Open Interventions', note: 'Active support cases', color: '#00897b' }
];

const roadmap = [
    ['Sprint 1', 'Foundation & database design', 'Complete'],
    ['Sprint 2', 'Accounts, roles & permissions', 'Complete'],
    ['Sprint 3', 'Student and academic records', 'Complete'],
    ['Sprint 4', 'Attendance encoding', 'Complete'],
    ['Sprint 5', 'Summaries and dashboards', 'Complete'],
    ['Sprint 6', 'SMS notification workflow', 'Implemented'],
    ['Sprint 7', 'Interventions and home visits', 'Implemented'],
    ['Sprint 8', 'Explainable risk assessment', 'Implemented'],
    ['Sprint 9', 'Restricted well-being check-ins', 'Implemented'],
    ['Sprint 10', 'Reports and audit tools', 'Planned']
];

const Dashboard = () => {
    const account = useSelector((state) => state.account);
    const [data, setData] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        let active = true;
        axios.get(configData.API_SERVER + 'dashboard/summary/', {
            headers: { Authorization: `Token ${account.token}` }
        }).then((response) => {
            if (active) setData(response.data);
        }).catch(() => {
            if (active) setError('Dashboard data is unavailable. Make sure the Django server is running.');
        });
        return () => { active = false; };
    }, [account.token]);

    if (!data && !error) {
        return <Box sx={{ minHeight: 360, display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>;
    }

    const user = data?.user || account.user || {};
    const metrics = data?.metrics || {};
    const metricCards = data?.metric_cards || fallbackMetricCards;
    const attendanceOverview = data?.attendance_overview || { seven_day_trend: [] };
    const attendanceChartOptions = {
        chart: { stacked: true, toolbar: { show: false } },
        xaxis: { categories: attendanceOverview.seven_day_trend.map((item) => item.label) },
        colors: ['#43a047', '#fb8c00', '#e53935'], legend: { position: 'top' },
        dataLabels: { enabled: false }, yaxis: { min: 0, forceNiceScale: true }
    };

    return (
        <Grid container spacing={gridSpacing}>
            <Grid item xs={12}>
                <MainCard>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, flexDirection: { xs: 'column', sm: 'row' }, gap: 2 }}>
                        <Box>
                            <Typography variant="h2">Welcome, {user.first_name || user.username || 'TardyTrack user'}.</Typography>
                            <Typography sx={{ mt: 1 }} color="textSecondary">Attendance and dropout early-warning workspace</Typography>
                        </Box>
                        <Chip color="primary" label={user.role_label || 'Authorized user'} />
                    </Box>
                    {error && <Typography sx={{ mt: 2 }} color="error">{error}</Typography>}
                </MainCard>
            </Grid>

            {metricCards.map((metric) => (
                <Grid item lg={4} sm={6} xs={12} key={metric.key}>
                    <Card sx={{ height: '100%', borderLeft: `5px solid ${metric.color}` }}>
                        <CardContent>
                            <Typography color="textSecondary" variant="subtitle2">{metric.label}</Typography>
                            <Typography sx={{ my: 1 }} variant="h1">{metric.value ?? metrics[metric.key] ?? '—'}{metric.format === 'percent' ? '%' : ''}</Typography>
                            <Typography variant="caption">{metric.note}</Typography>
                        </CardContent>
                    </Card>
                </Grid>
            ))}

            <Grid item md={8} xs={12}>
                <MainCard title="Today’s attendance status">
                    <Grid container spacing={3}>
                        <Grid item sm={4} xs={12}>
                            <Typography variant="h3">{metrics.present_today ?? 0}</Typography>
                            <Typography color="textSecondary">Present</Typography>
                        </Grid>
                        <Grid item sm={4} xs={12}>
                            <Typography variant="h3">{metrics.late_today ?? 0}</Typography>
                            <Typography color="textSecondary">Late</Typography>
                        </Grid>
                        <Grid item sm={4} xs={12}>
                            <Typography variant="h3">{metrics.absent_today ?? 0}</Typography>
                            <Typography color="textSecondary">Absent</Typography>
                        </Grid>
                    </Grid>
                    <LinearProgress sx={{ mt: 4, height: 8, borderRadius: 4 }} variant="determinate" value={metrics.attendance_recorded_today ? 100 : 0} />
                    <Typography sx={{ mt: 1 }} variant="caption" color="textSecondary">Data as of {data?.as_of || 'today'}</Typography>
                </MainCard>
            </Grid>

            <Grid item xs={12}>
                <MainCard title={`Attendance overview · ${attendanceOverview.month_label || 'Current month'}`}>
                    <Grid container spacing={3}>
                        <Grid item md={3} xs={12}>
                            <Typography variant="h1">{attendanceOverview.attendance_rate || 0}%</Typography>
                            <Typography color="textSecondary">Monthly attendance rate</Typography>
                            <Typography sx={{ mt: 2 }} variant="body2">{attendanceOverview.attended || 0} attended · {attendanceOverview.absences || 0} absent · {attendanceOverview.recorded || 0} recorded</Typography>
                        </Grid>
                        <Grid item md={9} xs={12}>
                            <Chart type="bar" height={240} options={attendanceChartOptions} series={[
                                { name: 'Present', data: attendanceOverview.seven_day_trend.map((item) => item.present) },
                                { name: 'Late', data: attendanceOverview.seven_day_trend.map((item) => item.late) },
                                { name: 'Absent', data: attendanceOverview.seven_day_trend.map((item) => item.absent) }
                            ]} />
                        </Grid>
                    </Grid>
                </MainCard>
            </Grid>

            <Grid item md={4} xs={12}>
                <MainCard title="Development roadmap">
                    {roadmap.map(([sprint, scope, status]) => (
                        <Box key={sprint} sx={{ py: 1.25, borderBottom: '1px solid', borderColor: 'grey.100' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                                <Typography variant="subtitle1">{sprint}</Typography>
                                <Chip size="small" color={status === 'Complete' ? 'primary' : 'default'} label={status} />
                            </Box>
                            <Typography variant="caption" color="textSecondary">{scope}</Typography>
                        </Box>
                    ))}
                </MainCard>
            </Grid>
        </Grid>
    );
};

export default Dashboard;
