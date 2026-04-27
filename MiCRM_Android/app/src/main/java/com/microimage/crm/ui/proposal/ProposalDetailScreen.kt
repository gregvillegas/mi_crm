package com.microimage.crm.ui.proposal

import android.widget.Toast
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.ApprovalDecisionPayload
import com.microimage.crm.model.ProposalDetail
import com.microimage.crm.ui.customer.DetailRow
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProposalDetailScreen(token: String, proposalId: Int, navController: NavController) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var proposal by remember { mutableStateOf<ProposalDetail?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isActing by remember { mutableStateOf(false) }

    fun loadDetail() {
        isLoading = true
        scope.launch {
            try {
                val response = RetrofitClient.apiService.getProposalDetail("Token $token", proposalId)
                if (response.isSuccessful) {
                    proposal = response.body()
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

    LaunchedEffect(proposalId) { loadDetail() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(proposal?.proposalNumber ?: "Proposal Detail") },
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
            } else if (proposal != null) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    DetailRow("Subject", proposal!!.subject)
                    DetailRow("Customer", proposal!!.customer?.companyName ?: "N/A")
                    DetailRow("Total Amount", "${proposal!!.currency} ${String.format("%,.2f", proposal!!.totalAmount)}")
                    DetailRow("Status", proposal!!.statusDisplay)
                    DetailRow("Approval Status", proposal!!.approvalStatus)

                    Spacer(modifier = Modifier.height(24.dp))
                    Text("Line Items", style = MaterialTheme.typography.titleLarge)
                    proposal!!.items.forEach { item ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(item.description, fontWeight = FontWeight.Bold)
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Qty: ${item.quantity}", style = MaterialTheme.typography.bodySmall)
                                    Text("Price: ${String.format("%,.2f", item.unitPrice)}", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }

                    if (proposal!!.canCurrentUserApprove && !isActing) {
                        Spacer(modifier = Modifier.height(32.dp))
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(
                                onClick = {
                                    isActing = true
                                    scope.launch {
                                        val res = RetrofitClient.apiService.rejectProposal("Token $token", proposalId, ApprovalDecisionPayload("Rejected from App"))
                                        if (res.isSuccessful) {
                                            Toast.makeText(context, "Rejected", Toast.LENGTH_SHORT).show()
                                            loadDetail()
                                        }
                                        isActing = false
                                    }
                                },
                                modifier = Modifier.weight(1f),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.Red)
                            ) {
                                Text("Reject")
                            }
                            Button(
                                onClick = {
                                    isActing = true
                                    scope.launch {
                                        val res = RetrofitClient.apiService.approveProposal("Token $token", proposalId, ApprovalDecisionPayload("Approved from App"))
                                        if (res.isSuccessful) {
                                            Toast.makeText(context, "Approved", Toast.LENGTH_SHORT).show()
                                            loadDetail()
                                        }
                                        isActing = false
                                    }
                                },
                                modifier = Modifier.weight(1f),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
                            ) {
                                Text("Approve")
                            }
                        }
                    }
                }
            }
        }
    }
}
