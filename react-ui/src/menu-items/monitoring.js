import { IconBellRinging, IconBug, IconDeviceAnalytics, IconPhoneCall, IconReceipt2 } from '@tabler/icons';

export const monitoring = {
    id: 'tardytrack-modules',
    title: 'TardyTrack Modules',
    caption: 'Implemented by sprint',
    type: 'group',
    children: [
        { id: 'students', title: 'Students & Guardians', type: 'item', url: '/module/students', icon: IconDeviceAnalytics, breadcrumbs: false },
        { id: 'attendance', title: 'Attendance', type: 'item', url: '/module/attendance', icon: IconReceipt2, breadcrumbs: false },
        { id: 'risk', title: 'Risk Assessment', type: 'item', url: '/module/risk', icon: IconBug, breadcrumbs: false },
        { id: 'interventions', title: 'Interventions & Visits', type: 'item', url: '/module/interventions', icon: IconPhoneCall, breadcrumbs: false },
        { id: 'notifications', title: 'SMS Notifications', type: 'item', url: '/module/notifications', icon: IconBellRinging, breadcrumbs: false },
        { id: 'reports', title: 'Reports & Audit Logs', type: 'item', url: '/module/reports', icon: IconReceipt2, breadcrumbs: false }
    ]
};
