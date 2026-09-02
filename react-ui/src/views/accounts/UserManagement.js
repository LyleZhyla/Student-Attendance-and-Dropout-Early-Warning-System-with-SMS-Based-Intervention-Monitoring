import React from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';
import {
    Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent,
    DialogTitle, FormControl, Grid, InputLabel, MenuItem, Select, Table,
    TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography
} from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';

const emptyForm = {
    username: '', email: '', first_name: '', last_name: '', role: 'STUDENT',
    password: '', password_confirm: ''
};

const errorMessage = (error) => {
    const data = error.response?.data;
    if (!data) return 'Unable to connect to TardyTrack.';
    if (data.message) return data.message;
    return Object.entries(data).map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(' ') : messages}`).join(' ');
};

const UserManagement = () => {
    const account = useSelector((state) => state.account);
    const headers = React.useMemo(() => ({ Authorization: `Token ${account.token}` }), [account.token]);
    const [users, setUsers] = React.useState([]);
    const [roles, setRoles] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [search, setSearch] = React.useState('');
    const [roleFilter, setRoleFilter] = React.useState('');
    const [formOpen, setFormOpen] = React.useState(false);
    const [editing, setEditing] = React.useState(null);
    const [form, setForm] = React.useState(emptyForm);
    const [saving, setSaving] = React.useState(false);
    const [resetTarget, setResetTarget] = React.useState(null);
    const [resetForm, setResetForm] = React.useState({ temporary_password: '', temporary_password_confirm: '' });

    const loadUsers = React.useCallback(() => {
        setLoading(true);
        setError('');
        axios.get(configData.API_SERVER + 'accounts/users/', {
            headers,
            params: { search, role: roleFilter }
        }).then((response) => {
            setUsers(response.data.users);
            setRoles(response.data.roles);
        }).catch((requestError) => setError(errorMessage(requestError)))
            .finally(() => setLoading(false));
    }, [headers, roleFilter, search]);

    React.useEffect(() => {
        const timer = setTimeout(loadUsers, 250);
        return () => clearTimeout(timer);
    }, [loadUsers]);

    const openCreate = () => {
        setEditing(null);
        setForm(emptyForm);
        setError('');
        setFormOpen(true);
    };

    const openEdit = (user) => {
        setEditing(user);
        setForm({
            username: user.username, email: user.email || '', first_name: user.first_name || '',
            last_name: user.last_name || '', role: user.role, password: '', password_confirm: ''
        });
        setError('');
        setFormOpen(true);
    };

    const updateField = (event) => setForm({ ...form, [event.target.name]: event.target.value });

    const saveUser = () => {
        setSaving(true);
        setError('');
        const request = editing
            ? axios.patch(configData.API_SERVER + `accounts/users/${editing.id}/`, form, { headers })
            : axios.post(configData.API_SERVER + 'accounts/users/', form, { headers });
        request.then(() => {
            setFormOpen(false);
            loadUsers();
        }).catch((requestError) => setError(errorMessage(requestError)))
            .finally(() => setSaving(false));
    };

    const setActive = (user, isActive) => {
        setError('');
        axios.post(
            configData.API_SERVER + `accounts/users/${user.id}/status/`,
            { is_active: isActive }, { headers }
        ).then(loadUsers).catch((requestError) => setError(errorMessage(requestError)));
    };

    const resetPassword = () => {
        setSaving(true);
        setError('');
        axios.post(
            configData.API_SERVER + `accounts/users/${resetTarget.id}/reset-password/`,
            resetForm, { headers }
        ).then(() => {
            setResetTarget(null);
            setResetForm({ temporary_password: '', temporary_password_confirm: '' });
            loadUsers();
        }).catch((requestError) => setError(errorMessage(requestError)))
            .finally(() => setSaving(false));
    };

    return (
        <Grid container spacing={3}>
            <Grid item xs={12}>
                <MainCard>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, flexDirection: { xs: 'column', sm: 'row' }, gap: 2 }}>
                        <Box>
                            <Typography variant="h2">User management</Typography>
                            <Typography color="textSecondary">Create accounts, assign roles, and control access.</Typography>
                        </Box>
                        <Button variant="contained" color="primary" onClick={openCreate}>Create account</Button>
                    </Box>
                </MainCard>
            </Grid>
            <Grid item xs={12}>
                <MainCard>
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item md={8} xs={12}>
                            <TextField fullWidth label="Search name, username, or email" value={search} onChange={(event) => setSearch(event.target.value)} />
                        </Grid>
                        <Grid item md={4} xs={12}>
                            <FormControl fullWidth>
                                <InputLabel>Role</InputLabel>
                                <Select value={roleFilter} label="Role" onChange={(event) => setRoleFilter(event.target.value)}>
                                    <MenuItem value="">All roles</MenuItem>
                                    {roles.map((role) => <MenuItem key={role.value} value={role.value}>{role.label}</MenuItem>)}
                                </Select>
                            </FormControl>
                        </Grid>
                    </Grid>
                    {error && <Typography sx={{ mb: 2 }} color="error">{error}</Typography>}
                    {loading ? <Box sx={{ p: 6, textAlign: 'center' }}><CircularProgress /></Box> : (
                        <TableContainer>
                            <Table>
                                <TableHead><TableRow>
                                    <TableCell>User</TableCell><TableCell>Role</TableCell><TableCell>Status</TableCell>
                                    <TableCell>Security</TableCell><TableCell align="right">Actions</TableCell>
                                </TableRow></TableHead>
                                <TableBody>
                                    {users.map((user) => (
                                        <TableRow key={user.id} hover>
                                            <TableCell>
                                                <Typography variant="subtitle1">{user.full_name}</Typography>
                                                <Typography variant="caption" color="textSecondary">{user.username} · {user.email || 'No email'}</Typography>
                                            </TableCell>
                                            <TableCell><Chip size="small" label={user.role_label} /></TableCell>
                                            <TableCell><Chip size="small" color={user.is_active ? 'primary' : 'default'} label={user.is_active ? 'Active' : 'Inactive'} /></TableCell>
                                            <TableCell>{user.must_change_password ? 'Password change required' : 'Up to date'}</TableCell>
                                            <TableCell align="right">
                                                <Button size="small" onClick={() => openEdit(user)}>Edit</Button>
                                                <Button size="small" onClick={() => { setResetTarget(user); setError(''); }}>Reset password</Button>
                                                <Button
                                                    size="small" color={user.is_active ? 'secondary' : 'primary'}
                                                    disabled={user.id === account.user?.id}
                                                    onClick={() => setActive(user, !user.is_active)}
                                                >{user.is_active ? 'Deactivate' : 'Activate'}</Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                    {!users.length && <TableRow><TableCell colSpan={5} align="center">No accounts found.</TableCell></TableRow>}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    )}
                </MainCard>
            </Grid>

            <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="sm">
                <DialogTitle>{editing ? 'Edit account' : 'Create account'}</DialogTitle>
                <DialogContent>
                    {error && <Typography sx={{ mb: 2 }} color="error">{error}</Typography>}
                    <Grid container spacing={2} sx={{ mt: 0.5 }}>
                        <Grid item sm={6} xs={12}><TextField fullWidth required name="first_name" label="First name" value={form.first_name} onChange={updateField} /></Grid>
                        <Grid item sm={6} xs={12}><TextField fullWidth required name="last_name" label="Last name" value={form.last_name} onChange={updateField} /></Grid>
                        <Grid item sm={6} xs={12}><TextField fullWidth required name="username" label="Username" value={form.username} onChange={updateField} /></Grid>
                        <Grid item sm={6} xs={12}><TextField fullWidth name="email" type="email" label="Email" value={form.email} onChange={updateField} /></Grid>
                        <Grid item xs={12}><FormControl fullWidth><InputLabel>Role</InputLabel><Select name="role" value={form.role} label="Role" onChange={updateField}>{roles.map((role) => <MenuItem key={role.value} value={role.value}>{role.label}</MenuItem>)}</Select></FormControl></Grid>
                        {!editing && <React.Fragment>
                            <Grid item sm={6} xs={12}><TextField fullWidth required name="password" type="password" label="Temporary password" value={form.password} onChange={updateField} /></Grid>
                            <Grid item sm={6} xs={12}><TextField fullWidth required name="password_confirm" type="password" label="Confirm password" value={form.password_confirm} onChange={updateField} /></Grid>
                            <Grid item xs={12}><Typography variant="caption">The user will be required to change this password at first sign-in.</Typography></Grid>
                        </React.Fragment>}
                    </Grid>
                </DialogContent>
                <DialogActions><Button onClick={() => setFormOpen(false)}>Cancel</Button><Button disabled={saving} variant="contained" onClick={saveUser}>{editing ? 'Save changes' : 'Create account'}</Button></DialogActions>
            </Dialog>

            <Dialog open={Boolean(resetTarget)} onClose={() => setResetTarget(null)} fullWidth maxWidth="xs">
                <DialogTitle>Reset {resetTarget?.username} password</DialogTitle>
                <DialogContent>
                    <Typography sx={{ mb: 2 }} color="textSecondary">All existing login tokens will be revoked.</Typography>
                    {error && <Typography sx={{ mb: 2 }} color="error">{error}</Typography>}
                    <TextField sx={{ mb: 2 }} fullWidth type="password" label="Temporary password" value={resetForm.temporary_password} onChange={(event) => setResetForm({ ...resetForm, temporary_password: event.target.value })} />
                    <TextField fullWidth type="password" label="Confirm temporary password" value={resetForm.temporary_password_confirm} onChange={(event) => setResetForm({ ...resetForm, temporary_password_confirm: event.target.value })} />
                </DialogContent>
                <DialogActions><Button onClick={() => setResetTarget(null)}>Cancel</Button><Button disabled={saving} variant="contained" onClick={resetPassword}>Reset password</Button></DialogActions>
            </Dialog>
        </Grid>
    );
};

export default UserManagement;
