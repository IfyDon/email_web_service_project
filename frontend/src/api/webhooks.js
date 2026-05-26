/*
import { get, post, patch, del } from './client';

export const webhooksApi = {
  list:       ()          => get('/webhooks/'),
  get:        (id)        => get(`/webhooks/${id}/`),
  create:     (data)      => post('/webhooks/',        data),
  update:     (id, data)  => patch(`/webhooks/${id}/`, data),
  delete:     (id)        => del(`/webhooks/${id}/`),
  test:       (id)        => post(`/webhooks/${id}/test/`),
  deliveries: (id, params)=> get(`/webhooks/${id}/deliveries/`, params),
  retry:      (id, dlvId) => post(`/webhooks/${id}/deliveries/${dlvId}/retry/`),
};
*/