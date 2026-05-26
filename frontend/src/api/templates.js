/*
import { get, post, put, del } from './client';

export const templatesApi = {
  list:     ()        => get('/templates/'),
  get:      (id)      => get(`/templates/${id}/`),
  create:   (data)    => post('/templates/',        data),
  update:   (id, d)   => put(`/templates/${id}/`,   d),
  delete:   (id)      => del(`/templates/${id}/`),
  preview:  (id, ctx) => post(`/templates/${id}/preview/`, { context: ctx }),
  versions: (id)      => get(`/templates/${id}/versions/`),
  restore:  (id, ver) => post(`/templates/${id}/restore/`, { version_number: ver }),
};
*/