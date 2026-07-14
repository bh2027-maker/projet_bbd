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

export const discoverHouses = async (codeInsee) => {
  const { data } = await api.post(`/communes/${codeInsee}/discover`);
  return data;
};

export const fetchHouses = async (codeInsee, params = {}) => {
  const { data } = await api.get(`/communes/${codeInsee}/houses`, { params });
  return data;
};

export const fetchHouse = async (houseId) => {
  const { data } = await api.get(`/houses/${houseId}`);
  return data;
};

export const updateHouse = async (houseId, payload) => {
  const { data } = await api.patch(`/houses/${houseId}`, payload);
  return data;
};

export const fetchPipeline = async () => {
  const { data } = await api.get(`/pipeline`);
  return data;
};

export const fetchStatuses = async () => {
  const { data } = await api.get(`/pipeline/statuses`);
  return data;
};

export const fetchMairie = async (codeInsee) => {
  const { data } = await api.get(`/communes/${codeInsee}/mairie`);
  return data;
};

export const startDiscoveryAll = async () => {
  const { data } = await api.post(`/discovery/start`);
  return data;
};

export const fetchDiscoveryStatus = async () => {
  const { data } = await api.get(`/discovery/status`);
  return data;
};

export const startEnrichment = async () => {
  const { data } = await api.post(`/enrichment/start`);
  return data;
};

export const fetchEnrichmentStatus = async () => {
  const { data } = await api.get(`/enrichment/status`);
  return data;
};

export const fetchEcosysteme = async (codeInsee) => {
  const { data } = await api.get(`/communes/${codeInsee}/ecosysteme`);
  return data;
};

export const generateTourPdf = async (houseIds, label) => {
  const response = await api.post(`/tour/pdf`, { house_ids: houseIds, label }, {
    responseType: "blob",
  });
  return response.data;
};

export const statusColor = (status) => {
  return {
    a_analyser: "bg-slate-500/15 text-slate-300 border-slate-500/30",
    a_contacter: "bg-blue-500/15 text-blue-300 border-blue-500/40",
    interesse: "bg-cyan-500/15 text-cyan-300 border-cyan-500/40",
    rdv: "bg-purple-500/15 text-purple-300 border-purple-500/40",
    transmis_gael: "bg-amber-500/15 text-amber-300 border-amber-500/40",
    vendu: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
    perdu: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  }[status] || "bg-slate-500/15 text-slate-300 border-slate-500/30";
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
