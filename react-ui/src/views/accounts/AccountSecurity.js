import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useHistory } from 'react-router-dom';
import axios from 'axios';
import { Box, Button, Chip, Grid, TextField, Typography } from '@material-ui/core';

import configData from '../../config';
import MainCard from '../../ui-component/cards/MainCard';
import { ACCOUNT_INITIALIZE } from '../../store/actions';

const readError = (error) => {
    const data = error.response?.data;
    if (!data) return 'Unable to connect to TardyTrack.';
    if (data.message) return data.message;
    return Object.entries(data).map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(' ') : messages}`).join(' ');
};

const AccountSecurity = () => {
    const account = useSelector((state) => state.account);
    const dispatch = useDispatch();
    const history = useHistory();
    const [form, setForm] = React.useState({ current_password: '', new_password: '', new_password_confirm: '' });
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [success, setSuccess] = React.useState('');

    const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
    const submit = (event) => {
        event.preventDefault();
        setSaving(true);
        setError('');
        setSuccess('');
        axios.post(configData.API_SERVER + 'account/change-password/', form, {
            headers: { Authorization: `Token ${account.token}` }
        }).then((response) => {
            dispatch({
                type: ACCOUNT_INITIALIZE,
                payload: { isLoggedIn: true, token: response.data.token, user: response.data.user }
            });
            setForm({ current_password: '', new_password: '', new_password_confirm: '' });
            setSuccess('Password changed successfully. Your previous login token has been revoked.');
            setTimeout(() => history.push('/dashboard'), 900);
        }).catch((requestError) => setError(readError(requestError)))
            .finally(() => setSaving(false));
    };

    return (
        <Grid container spacing={3}>
            <Grid item md={7} xs={12}>
                <MainCard>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, alignItems: 'flex-start' }}>
                        <Box>
                            <Typography variant="h2">Password & security</Typography>
                            <Typography sx={{ mt: 1 }} color="textSecondary">Use a unique password that is not shared with another account.</Typography>
                        </Box>
                        {account.user?.must_change_password && <Chip color="secondary" label="Change required" />}
                    </Box>
                    {account.user?.must_change_password && (
                        <Box sx={{ mt: 3, p: 2, bgcolor: 'warning.light', borderRadius: 2 }}>
                            <Typography variant="subtitle1">Temporary password detected</Typography>
                            <Typography variant="body2">You must set a new password before accessing the other TardyTrack modules.</Typography>
                        </Box>
                    )}
                    <Box component="form" onSubmit={submit} sx={{ mt: 3 }}>
                        <TextField sx={{ mb: 2 }} fullWidth required type="password" name="current_password" label="Current password" value={form.current_password} onChange={update} />
                        <TextField sx={{ mb: 2 }} fullWidth required type="password" name="new_password" label="New password" value={form.new_password} onChange={update} />
                        <TextField fullWidth required type="password" name="new_password_confirm" label="Confirm new password" value={form.new_password_confirm} onChange={update} />
                        <Typography sx={{ mt: 2 }} variant="caption" color="textSecondary">Use at least 8 characters and avoid common or entirely numeric passwords.</Typography>
                        {error && <Typography sx={{ mt: 2 }} color="error">{error}</Typography>}
                        {success && <Typography sx={{ mt: 2 }} color="primary">{success}</Typography>}
                        <Button sx={{ mt: 3 }} type="submit" disabled={saving} variant="contained" color="primary">Change password</Button>
                    </Box>
                </MainCard>
            </Grid>
            <Grid item md={5} xs={12}>
                <MainCard title="Account access">
                    <Typography variant="subtitle1">{account.user?.full_name}</Typography>
                    <Typography color="textSecondary">{account.user?.role_label}</Typography>
                    <Box sx={{ mt: 3, p: 2, border: '1px solid', borderColor: 'grey.200', borderRadius: 2 }}>
                        <Typography variant="body2">If you believe another person accessed your account, change your password and contact the system administrator.</Typography>
                    </Box>
                </MainCard>
            </Grid>
        </Grid>
    );
};

export default AccountSecurity;
