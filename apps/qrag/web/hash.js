const crypto = require('crypto');

async function generateAlternateID(email) {
  // Use the built-in crypto module to hash the email using SHA-256
  const hash = crypto.createHash('sha256');
  hash.update(email);
  const hashHex = hash.digest('hex');
  return hashHex;
}

// generateAlternateID('[REDACTED-EMAIL]').then(alternateID => {
//   console.log('Alternate ID:', alternateID);
// });

// alternate ID for [REDACTED-EMAIL] is: 43140c096f4d525e
// this SHA 256 hash produces cd01a3eb69930b1d5b7be32dc52b38ee883aa87fdd12fe2da2c60b1d8d07876f


function generateSecureUserID(email) {
  const secretKey = 'your-secret-key'; // Keep this key secure and don't expose it publicly
  return CryptoJS.HmacSHA256(email, secretKey).toString();
}


