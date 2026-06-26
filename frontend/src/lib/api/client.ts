import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// Create AXIOS instance configured for JSON requests
const client = axios.create({
  baseURL: (import.meta.env.VITE_API_URL as string) || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach authentication token if stored
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: unknown) => Promise.reject(error)
);

// Response Interceptor: centralized error format mapping
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
          // Format validation error arrays from Pydantic
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
