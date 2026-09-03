import React from 'react';
import { Box, Typography } from '@material-ui/core';

const Logo = () => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box
            component="img"
            src={`${process.env.PUBLIC_URL}/tardytrack-logo.png`}
            alt="TardyTrack logo"
            sx={{
                display: 'block',
                width: 46,
                height: 46,
                flexShrink: 0,
                objectFit: 'contain'
            }}
        />
        <Box>
            <Typography component="div" sx={{ fontSize: 19, fontWeight: 800, lineHeight: 1, color: 'grey.900' }}>
                TardyTrack
            </Typography>
            <Typography component="div" sx={{ mt: 0.4, fontSize: 9, lineHeight: 1, letterSpacing: '0.12em', color: 'text.secondary' }}>
                EARLY WARNING SYSTEM
            </Typography>
        </Box>
    </Box>
);

export default Logo;
