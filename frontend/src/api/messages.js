
import { get, post } from './client';

export const messagesApi = {
  list:   (params) => get('/messages/',    params),
  get:    (id)     => get(`/messages/${id}/`),
  send:   (data)   => post('/send',        data),
  bulk:   (data)   => post('/send/bulk',   data),
};
