import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 60000 });

export const fetchCommunes = async (params = {}) => {
  const { data } = await api.get("/communes", { params });
  return data;
};

export const fetchCommune = async (codeInsee) => {
  const { data } = await api.get(`/communes/${codeInsee}`);
  return data;
};

export const fetchStats = async () => {
  const { data } = await api.get("/stats");
  return data;
};

export const generateAiComment = async (codeInsee) => {
  const { data } = await api.post(`/communes/${codeInsee}/ai-comment`);
  return data;
};

export const scoreColor = (score) => {
  if (score >= 70) return "score-high";
  if (score >= 55) return "score-medium";
  return "score-low";
};

export const scoreLabel = (score) => {
  if (score >= 80) return "Priorité 1";
  if (score >= 70) return "Priorité 2";
  if (score >= 55) return "À qualifier";
  return "Faible";
};
