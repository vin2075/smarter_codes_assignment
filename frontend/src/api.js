// ---------- api.js ----------
import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
});

export const searchHTML = async (url, query) => {
  const response = await API.post("/search", { url, query });
  return response.data;
};
