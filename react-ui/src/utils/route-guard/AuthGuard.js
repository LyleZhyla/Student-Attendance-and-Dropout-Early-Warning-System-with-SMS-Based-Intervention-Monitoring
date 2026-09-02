import PropTypes from 'prop-types';
import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Redirect } from 'react-router-dom';
import axios from 'axios';

import configData from '../../config';
import Loader from '../../ui-component/Loader';
import { ACCOUNT_INITIALIZE, LOGOUT } from '../../store/actions';

//-----------------------|| AUTH GUARD ||-----------------------//

/**
 * Authentication guard for routes
 * @param {PropTypes.node} children children element/node
 */
const AuthGuard = ({ children }) => {
    const account = useSelector((state) => state.account);
    const dispatch = useDispatch();
    const { isLoggedIn, token } = account;
    const [validating, setValidating] = React.useState(Boolean(isLoggedIn && token));

    React.useEffect(() => {
        let active = true;
        if (!isLoggedIn || !token) {
            setValidating(false);
            return () => { active = false; };
        }
        setValidating(true);
        axios.get(configData.API_SERVER + 'auth/me/', { headers: { Authorization: `Token ${token}` } })
            .then((response) => {
                if (active) dispatch({
                    type: ACCOUNT_INITIALIZE,
                    payload: { isLoggedIn: true, token, user: response.data.user }
                });
            })
            .catch(() => {
                if (active) dispatch({ type: LOGOUT });
            })
            .finally(() => {
                if (active) setValidating(false);
            });
        return () => { active = false; };
    }, [dispatch, isLoggedIn, token]);

    if (validating) {
        return <Loader />;
    }

    if (!isLoggedIn) {
        return <Redirect to="/login" />;
    }

    return children;
};

AuthGuard.propTypes = {
    children: PropTypes.node
};

export default AuthGuard;
