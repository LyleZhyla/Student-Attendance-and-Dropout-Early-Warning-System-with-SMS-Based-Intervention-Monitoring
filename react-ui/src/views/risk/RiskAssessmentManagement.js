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

const today = () => {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
const errorMessage = (error) => error.response?.data?.message || Object.entries(error.response?.data || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ') || 'Unable to load risk assessments.';
const levelColor = { LOW: '#43a047', MODERATE: '#fb8c00', HIGH: '#d81b60' };

const RiskAssessmentManagement = () => {
    const token = useSelector((state) => state.account.token);
    const headers = React.useMemo(() => ({ Authorization: `Token ${token}` }), [token]);
    const [records, setRecords] = React.useState([]);
    const [summary, setSummary] = React.useState({});
    const [options, setOptions] = React.useState({ students: [], levels: [], decisions: [], can_review: false });
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [notice, setNotice] = React.useState('');
    const [search, setSearch] = React.useState('');
    const [level, setLevel] = React.useState('');
    const [decisionFilter, setDecisionFilter] = React.useState('');
    const [generateForm, setGenerateForm] = React.useState({ student: '', assessed_on: today() });
    const [selected, setSelected] = React.useState(null);
    const [review, setReview] = React.useState({ decision: 'CONFIRMED', notes: '' });

    const load = React.useCallback(() => {
        setLoading(true); setError('');
        Promise.all([
            axios.get(configData.API_SERVER + 'risk-assessments/', { headers, params: { search, level, decision: decisionFilter } }),
            axios.get(configData.API_SERVER + 'risk-assessments/options/', { headers })
        ]).then(([assessmentResponse, optionResponse]) => {
            setRecords(assessmentResponse.data.records); setSummary(assessmentResponse.data.summary); setOptions(optionResponse.data);
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setLoading(false));
    }, [headers, search, level, decisionFilter]);

    React.useEffect(load, [load]);

    const generate = () => {
        setSaving(true); setError(''); setNotice('');
        axios.post(configData.API_SERVER + 'risk-assessments/generate/', {
            student: generateForm.student || null, assessed_on: generateForm.assessed_on
        }, { headers }).then((response) => {
            const conflicts = response.data.reviewed_conflicts?.length || 0;
            setNotice(`Generated or recalculated ${response.data.generated} draft assessment(s).${conflicts ? ` ${conflicts} reviewed result(s) were preserved.` : ''}`);
            load();
        }).catch((requestError) => setError(errorMessage(requestError))).finally(() => setSaving(false));
    };

    const openDetails = (record) => {
        setSelected(record); setReview({ decision: record.review_decision === 'PENDING' ? 'CONFIRMED' : record.review_decision, notes: record.reviewer_notes || '' });
        setError(''); setNotice('');
    };

    const submitReview = () => {
        setSaving(true); setError(''); setNotice('');
        axios.post(configData.API_SERVER + `risk-assessments/${selected.id}/review/`, review, { headers })
            .then((response) => { setSelected(response.data.record); setNotice('Human review recorded.'); load(); })
            .catch((requestError) => setError(errorMessage(requestError))).finally(() => setSaving(false));
    };

    const cards = [
        ['Pending review', summary.PENDING || 0, '#8e24aa'],
        ['High', summary.HIGH || 0, '#d81b60'],
        ['Moderate', summary.MODERATE || 0, '#fb8c00'],
        ['Low', summary.LOW || 0, '#43a047']
    ];
    const metrics = selected?.indicators?.metrics || {};
    const components = selected?.indicators?.components || [];

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard><Typography variant="h2">Risk assessment</Typography><Typography color="textSecondary">Transparent early-warning indicators for support planning. Scores require human review and are not diagnoses or disciplinary decisions.</Typography></MainCard></Grid>
        {cards.map(([label, value, color]) => <Grid key={label} item lg={3} sm={6} xs={12}><Card sx={{ borderLeft: `5px solid ${color}` }}><CardContent><Typography color="textSecondary">{label}</Typography><Typography variant="h2">{value}</Typography></CardContent></Card></Grid>)}

        {options.can_review && <Grid item xs={12}><MainCard title="Generate draft assessments">
            <Typography color="textSecondary" sx={{ mb: 2 }}>Uses the {options.policy_version} policy. Leave Student blank to assess every active student; reviewed results for the selected date are preserved.</Typography>
            <Grid container spacing={2} alignItems="flex-end">
                <Grid item md={6} xs={12}><FormControl fullWidth><InputLabel>Student</InputLabel><Select value={generateForm.student} label="Student" onChange={(event) => setGenerateForm({ ...generateForm, student: event.target.value })}><MenuItem value=""><em>All active students</em></MenuItem>{options.students.map((item) => <MenuItem key={item.id} value={item.id}>{item.name} · {item.lrn}</MenuItem>)}</Select></FormControl></Grid>
                <Grid item md={3} xs={12}><TextField fullWidth type="date" label="Assessment date" value={generateForm.assessed_on} inputProps={{ max: today() }} InputLabelProps={{ shrink: true }} onChange={(event) => setGenerateForm({ ...generateForm, assessed_on: event.target.value })} /></Grid>
                <Grid item md={3} xs={12}><Button fullWidth variant="contained" disabled={saving || !generateForm.assessed_on} onClick={generate}>{saving ? 'Generating…' : 'Generate draft'}</Button></Grid>
            </Grid>
            {notice && <Typography sx={{ mt: 2, color: 'success.main' }}>{notice}</Typography>}{error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
        </MainCard></Grid>}

        <Grid item xs={12}><MainCard title="Assessment register">
            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <TextField size="small" label="Search student or LRN" value={search} onChange={(event) => setSearch(event.target.value)} />
                <FormControl size="small" sx={{ minWidth: 150 }}><InputLabel>Level</InputLabel><Select value={level} label="Level" onChange={(event) => setLevel(event.target.value)}><MenuItem value=""><em>All levels</em></MenuItem>{options.levels.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl>
                {options.can_review && <FormControl size="small" sx={{ minWidth: 190 }}><InputLabel>Review decision</InputLabel><Select value={decisionFilter} label="Review decision" onChange={(event) => setDecisionFilter(event.target.value)}><MenuItem value=""><em>All decisions</em></MenuItem>{options.decisions.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl>}
            </Box>
            {error && !selected && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
            {loading ? <Box sx={{ p: 5, textAlign: 'center' }}><CircularProgress /></Box> : <TableContainer><Table>
                <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Student</TableCell><TableCell align="right">Score</TableCell><TableCell>Level</TableCell><TableCell>Review</TableCell><TableCell>Period</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead>
                <TableBody>{records.map((record) => <TableRow key={record.id} hover><TableCell>{record.assessed_on}</TableCell><TableCell>{record.student_name}<br/><Typography variant="caption">{record.learner_reference_number}</Typography></TableCell><TableCell align="right"><Typography variant="h4">{record.score}</Typography></TableCell><TableCell><Typography sx={{ color: levelColor[record.level], fontWeight: 600 }}>{record.level_label}</Typography></TableCell><TableCell>{record.review_decision_label}<br/><Typography variant="caption">{record.reviewed_by_name || 'Awaiting reviewer'}</Typography></TableCell><TableCell>{record.period_start} to {record.period_end}</TableCell><TableCell align="right"><Button size="small" onClick={() => openDetails(record)}>Explain</Button></TableCell></TableRow>)}
                    {!records.length && <TableRow><TableCell colSpan={7} align="center">No risk assessments found.</TableCell></TableRow>}
                </TableBody>
            </Table></TableContainer>}
        </MainCard></Grid>

        <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="md"><DialogTitle>{selected ? `${selected.student_name} — ${selected.score} (${selected.level_label})` : 'Assessment'}</DialogTitle><DialogContent>
            {selected && <>
                <Typography color="textSecondary">Assessment window: {selected.period_start} to {selected.period_end} · Policy: {selected.policy_version}</Typography>
                <Grid container spacing={2} sx={{ my: 1 }}><Grid item sm={4} xs={12}><Card variant="outlined"><CardContent><Typography color="textSecondary">Current attendance</Typography><Typography variant="h3">{metrics.current_attendance_rate || 0}%</Typography><Typography variant="caption">{metrics.current_recorded_sessions || 0} recorded sessions</Typography></CardContent></Card></Grid><Grid item sm={4} xs={12}><Card variant="outlined"><CardContent><Typography color="textSecondary">Previous attendance</Typography><Typography variant="h3">{metrics.previous_attendance_rate || 0}%</Typography><Typography variant="caption">{metrics.previous_recorded_sessions || 0} recorded sessions</Typography></CardContent></Card></Grid><Grid item sm={4} xs={12}><Card variant="outlined"><CardContent><Typography color="textSecondary">Review state</Typography><Typography variant="h4">{selected.review_decision_label}</Typography><Typography variant="caption">{selected.reviewed_by_name || 'Not reviewed'}</Typography></CardContent></Card></Grid></Grid>
                <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Indicator</TableCell><TableCell align="right">Observed</TableCell><TableCell align="right">Points</TableCell><TableCell>Rule</TableCell></TableRow></TableHead><TableBody>{components.map((item) => <TableRow key={item.key}><TableCell>{item.label}</TableCell><TableCell align="right">{item.value}{item.unit ? ` ${item.unit}` : ''}</TableCell><TableCell align="right">{item.points} / {item.max_points}</TableCell><TableCell>{item.explanation}</TableCell></TableRow>)}</TableBody></Table></TableContainer>
                <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 2 }}>{selected.indicators?.disclaimer}</Typography>
                {options.can_review && <Box sx={{ mt: 3 }}><Typography variant="h3" sx={{ mb: 2 }}>Human review</Typography><Grid container spacing={2}><Grid item md={4} xs={12}><FormControl fullWidth><InputLabel>Decision</InputLabel><Select value={review.decision} label="Decision" onChange={(event) => setReview({ ...review, decision: event.target.value })}>{options.decisions.filter((item) => item.value !== 'PENDING').map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</Select></FormControl></Grid><Grid item md={8} xs={12}><TextField fullWidth multiline minRows={2} label="Reviewer notes" value={review.notes} onChange={(event) => setReview({ ...review, notes: event.target.value })} /></Grid></Grid></Box>}
                {notice && <Typography sx={{ mt: 2, color: 'success.main' }}>{notice}</Typography>}{error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
            </>}
        </DialogContent><DialogActions><Button onClick={() => setSelected(null)}>Close</Button>{options.can_review && <Button variant="contained" disabled={saving || (['DISMISSED', 'NEEDS_MORE_INFO'].includes(review.decision) && !review.notes.trim())} onClick={submitReview}>{saving ? 'Saving…' : 'Record review'}</Button>}</DialogActions></Dialog>
    </Grid>;
};

export default RiskAssessmentManagement;
