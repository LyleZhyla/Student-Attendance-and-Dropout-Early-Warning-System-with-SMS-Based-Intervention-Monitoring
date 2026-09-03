import { IconBellRinging, IconBook, IconBug, IconDeviceAnalytics, IconPhoneCall, IconReceipt2 } from '@tabler/icons';

export const monitoring = {
    id: 'tardytrack-modules',
    title: 'TardyTrack Modules',
    caption: 'Implemented by sprint',
    type: 'group',
    children: [
        { id: 'academics', title: 'Academic Setup', type: 'item', url: '/academics', icon: IconBook, breadcrumbs: false, roles: ['ADMIN'] },
        { id: 'students', title: 'Students & Guardians', type: 'item', url: '/students', icon: IconDeviceAnalytics, breadcrumbs: false, roles: ['ADMIN'] },
        { id: 'attendance', title: 'Attendance', type: 'item', url: '/attendance', icon: IconReceipt2, breadcrumbs: false, roles: ['ADMIN', 'TEACHER', 'STUDENT', 'PARENT'] },
        { id: 'attendance-analytics', title: 'Attendance Analytics', type: 'item', url: '/attendance/analytics', icon: IconDeviceAnalytics, breadcrumbs: false, roles: ['ADMIN', 'TEACHER', 'STUDENT', 'PARENT'] },
        { id: 'risk', title: 'Risk Assessment', type: 'item', url: '/module/risk', icon: IconBug, breadcrumbs: false },
        { id: 'interventions', title: 'Interventions & Visits', type: 'item', url: '/module/interventions', icon: IconPhoneCall, breadcrumbs: false, roles: ['ADMIN', 'TEACHER', 'GUIDANCE'] },
        { id: 'notifications', title: 'SMS Notifications', type: 'item', url: '/module/notifications', icon: IconBellRinging, breadcrumbs: false, roles: ['ADMIN'] },
        { id: 'reports', title: 'Reports & Audit Logs', type: 'item', url: '/module/reports', icon: IconReceipt2, breadcrumbs: false, roles: ['ADMIN', 'GUIDANCE'] }
    ]
};
