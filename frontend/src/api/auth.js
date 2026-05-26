import { get, post, patch, del } from './client';

export const authApi = {
  signup:      (data)   => post('/auth/signup/',          data),
  login:       (data)   => post('/auth/login/',           data),
  login2fa:    (data)   => post('/auth/login/2fa/',       data),
  logout:      ()       => post('/auth/logout/'),
  me:          ()       => get('/auth/me/'),
  updateMe:    (data)   => patch('/auth/me/',             data),
  changePassword: (d)   => post('/auth/change-password/', d),
  passwordResetRequest:(d) => post('/auth/password-reset/request/', d),
  passwordResetConfirm:(d) => post('/auth/password-reset/confirm/', d),

  // API Keys
  listApiKeys:   ()     => get('/auth/api-keys/'),
  createApiKey:  (data) => post('/auth/api-keys/',        data),
  revokeApiKey:  (id)   => del(`/auth/api-keys/${id}/`),

  // 2FA
  twoFaSetup:    ()     => get('/auth/2fa/setup/'),
  twoFaVerify:   (data) => post('/auth/2fa/verify/',      data),
  twoFaDisable:  (data) => post('/auth/2fa/disable/',     data),
  backupCodes:   ()     => get('/auth/2fa/backup-codes/'),
};
