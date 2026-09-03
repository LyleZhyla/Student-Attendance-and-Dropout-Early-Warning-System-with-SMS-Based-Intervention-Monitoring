import React, { lazy } from 'react';
import { Route, Switch, useLocation } from 'react-router-dom';

// project imports
import MainLayout from './../layout/MainLayout';
import Loadable from '../ui-component/Loadable';
import AuthGuard from './../utils/route-guard/AuthGuard';

// dashboard routing
const DashboardDefault = Loadable(lazy(() => import('../views/dashboard/Default')));
const ModuleStatus = Loadable(lazy(() => import('../views/module-status')));
const UserManagement = Loadable(lazy(() => import('../views/accounts/UserManagement')));
const AccountSecurity = Loadable(lazy(() => import('../views/accounts/AccountSecurity')));
const AcademicManagement = Loadable(lazy(() => import('../views/academics/AcademicManagement')));
const StudentManagement = Loadable(lazy(() => import('../views/students/StudentManagement')));
const AttendanceManagement = Loadable(lazy(() => import('../views/attendance/AttendanceManagement')));
const AttendanceAnalytics = Loadable(lazy(() => import('../views/attendance/AttendanceAnalytics')));
const NotificationManagement = Loadable(lazy(() => import('../views/notifications/NotificationManagement')));
const InterventionManagement = Loadable(lazy(() => import('../views/interventions/InterventionManagement')));
const RiskAssessmentManagement = Loadable(lazy(() => import('../views/risk/RiskAssessmentManagement')));
const WellBeingManagement = Loadable(lazy(() => import('../views/well-being/WellBeingManagement')));

//-----------------------|| MAIN ROUTING ||-----------------------//

const MainRoutes = () => {
    const location = useLocation();

    return (
        <Route
            path={[
                '/dashboard',
                '/module/:moduleKey',
                '/accounts/users',
                '/account/security',
                '/academics',
                '/students',
                '/attendance',
                '/attendance/analytics',
                '/notifications',
                '/interventions',
                '/risk-assessments',
                '/well-being'
            ]}
        >
            <MainLayout>
                <Switch location={location} key={location.pathname}>
                    <AuthGuard>
                        <Route exact path="/dashboard" component={DashboardDefault} />
                        <Route exact path="/module/:moduleKey" component={ModuleStatus} />
                        <Route exact path="/accounts/users" component={UserManagement} />
                        <Route exact path="/account/security" component={AccountSecurity} />
                        <Route exact path="/academics" component={AcademicManagement} />
                        <Route exact path="/students" component={StudentManagement} />
                        <Route exact path="/attendance" component={AttendanceManagement} />
                        <Route exact path="/attendance/analytics" component={AttendanceAnalytics} />
                        <Route exact path="/notifications" component={NotificationManagement} />
                        <Route exact path="/interventions" component={InterventionManagement} />
                        <Route exact path="/risk-assessments" component={RiskAssessmentManagement} />
                        <Route exact path="/well-being" component={WellBeingManagement} />
                    </AuthGuard>
                </Switch>
            </MainLayout>
        </Route>
    );
};

export default MainRoutes;
