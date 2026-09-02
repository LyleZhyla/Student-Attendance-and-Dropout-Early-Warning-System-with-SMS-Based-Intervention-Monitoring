import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import axios from 'axios';
import { Avatar, Box, Chip, Divider, ListItemIcon, Menu, MenuItem, Typography } from '@material-ui/core';
import { IconLogout } from '@tabler/icons';
import { Link } from 'react-router-dom';

import configData from '../../../../config';
import { LOGOUT } from '../../../../store/actions';

const ProfileSection = () => {
    const account = useSelector((state) => state.account);
    const dispatch = useDispatch();
    const [anchorEl, setAnchorEl] = React.useState(null);
    const user = account.user || {};
    const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}` || user.username?.[0] || 'U';

    const handleLogout = () => {
        setAnchorEl(null);
        axios
            .post(configData.API_SERVER + 'auth/logout/', {}, { headers: { Authorization: `Token ${account.token}` } })
            .catch(() => null)
            .finally(() => dispatch({ type: LOGOUT }));
    };

    return (
        <React.Fragment>
            <Chip
                avatar={<Avatar>{initials.toUpperCase()}</Avatar>}
                label={user.first_name || user.username || 'Account'}
                color="primary"
                variant="outlined"
                onClick={(event) => setAnchorEl(event.currentTarget)}
                sx={{ fontWeight: 600 }}
            />
            <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={() => setAnchorEl(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
                <Box sx={{ minWidth: 250, px: 2, py: 1.5 }}>
                    <Typography variant="subtitle1">{user.full_name || user.username}</Typography>
                    <Typography variant="caption" color="textSecondary">{user.role_label || 'Authorized user'}</Typography>
                </Box>
                <Divider />
                <MenuItem component={Link} to="/account/security" onClick={() => setAnchorEl(null)}>
                    <Typography variant="body2">Password & security</Typography>
                </MenuItem>
                <MenuItem onClick={handleLogout}>
                    <ListItemIcon><IconLogout size="1.25rem" /></ListItemIcon>
                    <Typography variant="body2">Sign out</Typography>
                </MenuItem>
            </Menu>
        </React.Fragment>
    );
};

export default ProfileSection;
