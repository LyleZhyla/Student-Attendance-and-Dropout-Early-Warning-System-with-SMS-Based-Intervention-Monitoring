import React from 'react';
import { Box, Chip, Grid, Typography } from '@material-ui/core';
import { useParams } from 'react-router-dom';

import MainCard from '../../ui-component/cards/MainCard';

const modules = {
    students: { title: 'Students & Guardians', sprint: 'Sprint 3', detail: 'Student profiles, verified guardians, sections, advisers, schedules, enrollment, and CSV/Excel import.' },
    attendance: { title: 'Attendance', sprint: 'Sprint 4–5', detail: 'Bulk attendance encoding, correction controls, monthly summaries, trends, and role-specific monitoring.' },
    risk: { title: 'Risk Assessment', sprint: 'Sprint 8–9', detail: 'Explainable early-warning indicators, restricted well-being assessment, and required human review.' },
    interventions: { title: 'Interventions & Home Visits', sprint: 'Sprint 7', detail: 'Case ownership, parent contact attempts, meeting/home-visit schedules, findings, and follow-up.' },
    notifications: { title: 'SMS Notifications', sprint: 'Sprint 6', detail: 'Consent-aware manual and automated messages, duplicate prevention, retries, and delivery monitoring.' },
    reports: { title: 'Reports & Audit Logs', sprint: 'Sprint 10', detail: 'Printable attendance, intervention and risk reports plus an auditable history of material system activity.' }
};

const ModuleStatus = () => {
    const { moduleKey } = useParams();
    const module = modules[moduleKey] || { title: 'Module', sprint: 'Planned', detail: 'This module is part of the approved TardyTrack roadmap.' };

    return (
        <Grid container spacing={3}>
            <Grid item xs={12}>
                <MainCard>
                    <Box sx={{ maxWidth: 720, py: 3 }}>
                        <Chip color="primary" label={module.sprint} />
                        <Typography sx={{ mt: 2 }} variant="h1">{module.title}</Typography>
                        <Typography sx={{ mt: 2, fontSize: 16 }} color="textSecondary">{module.detail}</Typography>
                        <Box sx={{ mt: 4, p: 2, bgcolor: 'primary.light', borderRadius: 2 }}>
                            <Typography variant="subtitle1">Planned feature</Typography>
                            <Typography variant="body2">The database foundation exists. The complete workflow will be enabled in its assigned sprint to preserve validation, privacy, and access-control requirements.</Typography>
                        </Box>
                    </Box>
                </MainCard>
            </Grid>
        </Grid>
    );
};

export default ModuleStatus;
