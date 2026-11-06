/* Route-typed calls over the generated schema (plan 1.F1). A call names a route as the backend declares it, without the
   /storage prefix the Node relay adds: `apiGet('/weeks/{week_id}', { path: { week_id } })`. Its path parameters, query
   and answer are the generated types, so a renamed field or parameter fails `npm run lint` after `npm run api:types`. */
import type { paths } from './schema';
import { apiRequest, type RequestOptions } from './client';

type Prefix = '/storage';
export type Route = { [K in keyof paths]: K extends `${Prefix}${infer R}` ? R : never }[keyof paths];
export type Verb = 'get' | 'post' | 'patch' | 'put' | 'delete';

type Item<R extends Route> = paths[`${Prefix}${R}` & keyof paths];
type Operation<R extends Route, V extends Verb> = NonNullable<Item<R>[V & keyof Item<R>]>;
export type RoutesFor<V extends Verb> = { [R in Route]: [Operation<R, V>] extends [never] ? never : R }[Route];

type Json<T> = T extends { content: { 'application/json': infer J } } ? J : never;
export type ResponseOf<R extends Route, V extends Verb> =
  Operation<R, V> extends { responses: infer Rs } ? Json<Rs[keyof Rs & (200 | 201 | 202)]> : never;

type PathParams<O> = O extends { parameters: { path: infer P } } ? (P extends object ? P : never) : never;
type QueryParams<O> = O extends { parameters: { query?: infer Q } } ? NonNullable<Q> : never;
type BodyOf<O> = O extends { requestBody: { content: { 'application/json': infer B } } } ? B
  : O extends { requestBody?: { content: { 'application/json': infer B } } } ? B : never;

type Part<K extends string, T, Required extends boolean> = [T] extends [never] ? unknown : Required extends true ? { [P in K]: T } : { [P in K]?: T };
export type ReadArgs<R extends Route> = Part<'path', PathParams<Operation<R, 'get'>>, true> & Part<'query', QueryParams<Operation<R, 'get'>>, false>;
export type WriteArgs<R extends Route, V extends Verb> =
  Part<'path', PathParams<Operation<R, V>>, true> & Part<'query', QueryParams<Operation<R, V>>, false> & Part<'body', BodyOf<Operation<R, V>>, true>;

type Rest<A> = {} extends A ? [args?: A, options?: RequestOptions] : [args: A, options?: RequestOptions];

interface Args { path?: Record<string, string | number>; query?: Record<string, unknown>; body?: unknown }

/** The request path for a route with its path parameters and query filled in. Query values that are undefined, null
    or empty are left out, so a cleared filter does not reach the relay as an empty parameter. */
export function routePath(route: string, args: Args = {}): string {
  const path = route.replace(/\{(\w+)\}/g, (_match, name: string) => {
    const value = args.path?.[name];
    if (value === undefined || value === '') throw new Error(`Missing path parameter ${name} for ${route}`);
    return encodeURIComponent(String(value));
  });
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(args.query ?? {})) {
    if (value === undefined || value === null || value === '') continue;
    query.set(key, String(value));
  }
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}

export function apiGet<R extends RoutesFor<'get'>>(route: R, ...[args, options]: Rest<ReadArgs<R>>): Promise<ResponseOf<R, 'get'>> {
  return apiRequest(routePath(route, args as Args), 'GET', undefined, options);
}

export function apiSend<V extends 'post' | 'patch' | 'put', R extends RoutesFor<V>>(
  verb: V, route: R, ...[args, options]: Rest<WriteArgs<R, V>>): Promise<ResponseOf<R, V>> {
  const { body, ...rest } = (args ?? {}) as Args;
  return apiRequest(routePath(route, rest), verb.toUpperCase(), body ?? {}, options);
}

export const apiPost = <R extends RoutesFor<'post'>>(route: R, ...rest: Rest<WriteArgs<R, 'post'>>) => apiSend('post', route, ...rest);
export const apiPatch = <R extends RoutesFor<'patch'>>(route: R, ...rest: Rest<WriteArgs<R, 'patch'>>) => apiSend('patch', route, ...rest);
