package com.microimage.crm.ui.customer

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.CustomerDetail
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomerDetailScreen(token: String, customerId: Int, navController: NavController) {
    val scope = rememberCoroutineScope()
    var customer by remember { mutableStateOf<CustomerDetail?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(customerId) {
        scope.launch {
            try {
                val response = RetrofitClient.apiService.getCustomerDetail("Token $token", customerId)
                if (response.isSuccessful) {
                    customer = response.body()
                } else {
                    errorMessage = "Error: ${response.code()}"
                }
            } catch (e: Exception) {
                errorMessage = e.message
            } finally {
                isLoading = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(customer?.companyName ?: "Customer Detail") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (errorMessage != null) {
                Text(errorMessage!!, modifier = Modifier.align(Alignment.Center))
            } else if (customer != null) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    DetailRow("Company", customer!!.companyName)
                    DetailRow("Primary Contact", customer!!.contactPersonName)
                    DetailRow("Position", customer!!.contactPersonPosition ?: "N/A")
                    DetailRow("Email", customer!!.email)
                    DetailRow("Phone", customer!!.phoneNumber ?: "N/A")
                    DetailRow("Industry", customer!!.industry ?: "N/A")
                    DetailRow("Territory", customer!!.territory ?: "N/A")
                    DetailRow("Status", customer!!.displayStatus ?: "Active")
                    DetailRow("Salesperson", customer!!.salespersonName ?: "Unassigned")
                    
                    if (customer!!.contacts.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(24.dp))
                        Text("Other Contacts", style = MaterialTheme.typography.titleLarge)
                        customer!!.contacts.forEach { contact ->
                            Card(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                            ) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Text(contact.name, fontWeight = FontWeight.Bold)
                                    Text(contact.position ?: "", style = MaterialTheme.typography.bodySmall)
                                    Text(contact.email ?: "", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun DetailRow(label: String, value: String) {
    Column(modifier = Modifier.padding(vertical = 8.dp)) {
        Text(text = label, style = MaterialTheme.typography.labelMedium, color = Color.Gray)
        Text(text = value, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
        Divider(modifier = Modifier.padding(top = 8.dp))
    }
}
