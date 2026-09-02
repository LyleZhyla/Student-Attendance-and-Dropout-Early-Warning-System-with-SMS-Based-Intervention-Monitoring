import { IconKey } from '@tabler/icons';

export const accounts = {
    id: 'accounts',
    title: 'Accounts',
    type: 'group',
    children: [
        {
            id: 'user-management', title: 'User Management', type: 'item',
            url: '/accounts/users', icon: IconKey, breadcrumbs: false, roles: ['ADMIN']
        },
        {
            id: 'account-security', title: 'Password & Security', type: 'item',
            url: '/account/security', icon: IconKey, breadcrumbs: false
        }
    ]
};
