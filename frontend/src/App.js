import "./App.css";
import "./index.css";
import "leaflet/dist/leaflet.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import CommuneDetail from "./pages/CommuneDetail";
import { Toaster } from "sonner";

function App() {
  return (
    <div className="App bg-[#0B0F19] text-slate-200 min-h-screen grain">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/communes/:codeInsee" element={<CommuneDetail />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme="dark" position="bottom-right" />
    </div>
  );
}

export default App;
