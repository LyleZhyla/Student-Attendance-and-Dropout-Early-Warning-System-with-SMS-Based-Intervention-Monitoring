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
    'school-years': {
        title: 'School years', columns: [['name', 'School year'], ['starts_on', 'Starts'], ['ends_on', 'Ends'], ['is_active', 'Active']],
        empty: { name: '', starts_on: '', ends_on: '', is_active: false },
        fields: [['name', 'School year', 'text'], ['starts_on', 'Start date', 'date'], ['ends_on', 'End date', 'date'], ['is_active', 'Set as active', 'boolean']]
    },
    'grade-levels': {
        title: 'Grade levels', columns: [['name', 'Grade level'], ['order', 'Display order']], empty: { name: '', order: 1 },
        fields: [['name', 'Grade level', 'text'], ['order', 'Display order', 'number']]
    },
    subjects: {
        title: 'Subjects', columns: [['code', 'Code'], ['name', 'Subject name']], empty: { code: '', name: '' },
        fields: [['code', 'Subject code', 'text'], ['name', 'Subject name', 'text']]
    },
    sections: {
        title: 'Sections', columns: [['name', 'Section'], ['grade_level_name', 'Grade'], ['school_year_name', 'School year'], ['adviser_name', 'Adviser'], ['student_count', 'Students']],
        empty: { name: '', grade_level: '', school_year: '', adviser: '' },
        fields: [['name', 'Section name', 'text'], ['grade_level', 'Grade level', 'grade_levels'], ['school_year', 'School year', 'school_years'], ['adviser', 'Adviser', 'teachers']]
    },
    schedules: {
        title: 'Class schedules', columns: [['section_name', 'Section'], ['subject_name', 'Subject'], ['teacher_name', 'Teacher'], ['weekday_label', 'Day'], ['time', 'Time']],
        empty: { section: '', subject: '', teacher: '', weekday: 1, starts_at: '', ends_at: '' },
        fields: [['section', 'Section', 'sections'], ['subject', 'Subject', 'subjects'], ['teacher', 'Teacher', 'teachers'], ['weekday', 'Weekday', 'weekdays'], ['starts_at', 'Starts', 'time'], ['ends_at', 'Ends', 'time']]
    }
};

const message = (error) => error.response?.data?.message || Object.entries(error.response?.data || {})
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ') || 'Unable to connect to TardyTrack.';

const AcademicManagement = () => {
    const token = useSelector((state) => state.account.token);
    const headers = React.useMemo(() => ({ Authorization: `Token ${token}` }), [token]);
    const [tab, setTab] = React.useState('school-years');
    const [records, setRecords] = React.useState([]);
    const [options, setOptions] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [search, setSearch] = React.useState('');
    const [editing, setEditing] = React.useState(null);
    const [form, setForm] = React.useState(definitions[tab].empty);
    const [open, setOpen] = React.useState(false);
    const definition = definitions[tab];
    const visibleRecords = records.filter((record) => JSON.stringify(record).toLowerCase().includes(search.toLowerCase()));

    const load = React.useCallback(() => {
        setLoading(true); setError('');
        Promise.all([
            axios.get(configData.API_SERVER + `academics/${tab}/`, { headers }),
            axios.get(configData.API_SERVER + 'academics/options/', { headers })
        ]).then(([recordsResponse, optionsResponse]) => {
            setRecords(recordsResponse.data.records); setOptions(optionsResponse.data);
        }).catch((requestError) => setError(message(requestError))).finally(() => setLoading(false));
    }, [headers, tab]);

    React.useEffect(load, [load]);

    const begin = (record = null) => {
        setEditing(record);
        setForm(record ? definition.fields.reduce((values, [name]) => ({ ...values, [name]: record[name] ?? '' }), {}) : { ...definition.empty });
        setError(''); setOpen(true);
    };

    const save = () => {
        const url = configData.API_SERVER + `academics/${tab}/${editing ? `${editing.id}/` : ''}`;
        const request = editing ? axios.patch(url, form, { headers }) : axios.post(url, form, { headers });
        request.then(() => { setOpen(false); load(); }).catch((requestError) => setError(message(requestError)));
    };

    const display = (record, key) => {
        if (key === 'is_active') return record[key] ? 'Yes' : 'No';
        if (key === 'time') return `${record.starts_at}–${record.ends_at}`;
        return record[key] ?? '—';
    };

    const renderField = ([name, label, type]) => {
        if (type === 'boolean') return <Box key={name}><Checkbox checked={Boolean(form[name])} onChange={(event) => setForm({ ...form, [name]: event.target.checked })} />{label}</Box>;
        const choices = options[type];
        if (choices) return <FormControl key={name} fullWidth><InputLabel>{label}</InputLabel><Select value={form[name]} label={label} onChange={(event) => setForm({ ...form, [name]: event.target.value })}>
            {choices.map((choice) => <MenuItem key={choice.id ?? choice.value} value={choice.id ?? choice.value}>{choice.name ?? choice.label}</MenuItem>)}
        </Select></FormControl>;
        return <TextField key={name} fullWidth required name={name} label={label} type={type} value={form[name]} InputLabelProps={['date', 'time'].includes(type) ? { shrink: true } : undefined} onChange={(event) => setForm({ ...form, [name]: event.target.value })} />;
    };

    return <Grid container spacing={3}>
        <Grid item xs={12}><MainCard><Typography variant="h2">Academic setup</Typography><Typography color="textSecondary">Manage school years, grades, subjects, sections, advisers, and conflict-checked class schedules.</Typography></MainCard></Grid>
        <Grid item xs={12}><MainCard>
            <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable">
                {Object.entries(definitions).map(([key, value]) => <Tab key={key} value={key} label={value.title} />)}
            </Tabs>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, my: 2 }}><TextField size="small" label="Search" value={search} onChange={(event) => setSearch(event.target.value)} /><Button variant="contained" onClick={() => begin()}>Add {definition.title.toLowerCase().replace(/s$/, '')}</Button></Box>
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

export default AcademicManagement;
