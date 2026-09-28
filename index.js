// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";

// Configuração do Firebase
const firebaseConfig = {
  apiKey: "sua-api-key",
  authDomain: "seu-auth-domain",
  projectId: "seu-project-id",
  storageBucket: "seu-storage-bucket",
  messagingSenderId: "seu-messaging-sender-id",
  appId: "seu-app-id",
  measurementId: "seu-measurement-id"
};

// Inicialize o Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);