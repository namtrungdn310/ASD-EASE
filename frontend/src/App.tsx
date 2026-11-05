import {Dashboard} from "./pages/Dashboard";
import { LocalConnection } from "./components/LocalConnection";

export default function App() {
  return import.meta.env.DEV
    ? <LocalConnection><Dashboard /></LocalConnection>
    : <Dashboard />;
}

