import axios, { AxiosError } from 'axios';

const explicitApiUrl = import.meta.env.VITE_API_URL as string | undefined;

const client = axios.create({
  baseURL: explicitApiUrl ? `${explicitApiUrl.replace(/\/$/, '')}/api` : '/api',
  timeout: 600000,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    let message = 'An unexpected error occurred';

    if (error.response) {
      const responseData = error.response.data as { detail?: string | Array<{ loc: string[]; msg: string }> } | undefined;

      if (responseData && responseData.detail) {
        if (typeof responseData.detail === 'string') {
          message = responseData.detail;
        } else if (Array.isArray(responseData.detail)) {
          message = responseData.detail
            .map((err) => `${err.loc.slice(1).join('.')}: ${err.msg}`)
            .join(', ');
        }
      }
    } else if (error.request) {
      message = 'Server is unreachable. Please verify your connection.';
    }

    return Promise.reject(new Error(message));
  }
);

export default client;
