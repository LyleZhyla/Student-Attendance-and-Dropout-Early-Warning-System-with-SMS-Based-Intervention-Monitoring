import React from 'react';
import { Box, Typography } from '@material-ui/core';

const Logo = () => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box
            component="span"
            sx={{
                display: 'grid', placeItems: 'center', width: 36, height: 36,
                borderRadius: '11px', bgcolor: 'primary.main', color: 'white',
                fontSize: 20, fontWeight: 800
            }}
        >
            T
        </Box>
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
